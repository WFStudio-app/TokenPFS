"""Клиент Ollama /api/chat с поддержкой tool calling."""
import json
import urllib.error
import urllib.request


class LLMError(RuntimeError):
    pass


class ToolsUnsupported(LLMError):
    """Модель не умеет нативные вызовы инструментов — включаем JSON-режим."""


class OllamaClient:
    def __init__(self, url, model, num_ctx=4096, timeout=900):
        self.url = url.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.timeout = timeout

    def chat(self, messages, tools=None):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": self.num_ctx, "temperature": 0.2},
        }
        if tools:
            payload["tools"] = tools
        req = urllib.request.Request(
            self.url + "/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.load(resp)["message"]
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if "does not support tools" in body:
                raise ToolsUnsupported(body)
            raise LLMError(f"Ollama HTTP {e.code}: {body[:300]}")
        except urllib.error.URLError as e:
            raise LLMError(
                f"Ollama недоступна ({e.reason}). Запустите: ollama serve &"
            )

    def list_models(self):
        try:
            with urllib.request.urlopen(self.url + "/api/tags", timeout=10) as r:
                return [m["name"] for m in json.load(r).get("models", [])]
        except Exception:
            return []
