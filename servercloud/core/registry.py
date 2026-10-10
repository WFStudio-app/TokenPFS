"""Runtime registry: downloaded models get numbers [01],[02]... right after pull."""

import json
import os
import threading

_LOCK = threading.Lock()


class Registry:
    def __init__(self, path):
        self.path = path
        self.items = {}   # number(str "01") -> {"name":..., "size_gb":...}
        self._next = 1
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    data = json.load(f)
                self.items = {k: v for k, v in data.get("items", {}).items()}
                self._next = data.get("next", len(self.items) + 1)
            except Exception:
                pass

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"items": self.items, "next": self._next}, f, indent=2)
        os.replace(tmp, self.path)

    def add(self, name: str, size_gb: float) -> str:
        with _LOCK:
            num = f"{self._next:02d}"
            self.items[num] = {"name": name, "size_gb": size_gb}
            self._next += 1
            self.save()
            return num

    def find(self, key: str):
        """Accept '07', '7', or model name; return (number, entry) or (None, None)."""
        key = key.strip()
        with _LOCK:   # non-reentrant lock: callers must NOT hold it
            if key.zfill(2) in self.items:
                n = key.zfill(2)
                return n, self.items[n]
            for n, e in self.items.items():
                if e["name"] == key:
                    return n, e
        return None, None

    def remove(self, key: str):
        """Delete model by number ('07'/'7') or exact name. Returns (num, entry) or (None, None)."""
        num, entry = self.find(key)   # find() takes the lock itself
        if not num:
            return None, None
        with _LOCK:
            if num in self.items:
                del self.items[num]
                self.save()
                return num, entry
        return None, None

    def all(self):
        with _LOCK:
            return dict(sorted(self.items.items()))
