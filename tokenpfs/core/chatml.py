"""Chat context: per-model conversation history + system prompt.

/w becomes a chat mode: every question is appended to the model's
history and the full context (system + past turns) is sent to Ollama,
so the model remembers the dialogue. /clear resets it.
"""

import json
import os
import threading

MAX_TURNS = 20          # keep last N messages in context
IM_START = "<|" + "im_start" + "|>"
IM_END = "<|" + "im_end" + "|>"


class ChatStore:
    """Thread-safe store of histories and system prompts."""

    def __init__(self, path=None):
        self.path = path or os.path.expanduser("~/.tokenpfs/chat.json")
        self._lock = threading.Lock()
        self.histories = {}   # number -> [{"role","content"}, ...]
        self.system = {}      # number|"all" -> prompt text
        self.load()

    # ---------- persistence ----------
    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self.histories = {str(k): list(v) for k, v in data.get("histories", {}).items()}
            self.system = dict(data.get("system", {}))
        except Exception:
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"histories": self.histories, "system": self.system}, f)
            os.replace(tmp, self.path)
        except Exception:
            pass

    # ---------- system prompt ----------
    def set_system(self, target, text):
        with self._lock:
            if text:
                self.system[target] = text
            else:
                self.system.pop(target, None)
            self.save()

    def get_system(self, number):
        with self._lock:
            return self.system.get(str(number)) or self.system.get("all") or ""

    # ---------- history ----------
    def add(self, number, role, content):
        with self._lock:
            h = self.histories.setdefault(str(number), [])
            h.append({"role": role, "content": content})
            if len(h) > MAX_TURNS * 2:
                del h[: len(h) - MAX_TURNS * 2]
            self.save()

    def history(self, number):
        with self._lock:
            return list(self.histories.get(str(number), []))

    def clear(self, number=None):
        """Clear one model's history (or all when number is None)."""
        with self._lock:
            if number is None:
                self.histories.clear()
            else:
                self.histories.pop(str(number), None)
            self.save()

    # ---------- prompt building ----------
    def build_prompt(self, number, user_text):
        """Compose ChatML prompt: system + history + current user turn."""
        sys_p = self.get_system(number)
        parts = []
        if sys_p:
            parts.append(IM_START + "system\n" + sys_p + IM_END)
        for m in self.history(number):
            parts.append(IM_START + m["role"] + "\n" + m["content"] + IM_END)
        parts.append(IM_START + "user\n" + user_text + IM_END)
        parts.append(IM_START + "assistant\n")
        return "\n".join(parts)
