"""Generation options for Ollama (temperature, top_p, num_predict...).

Set via /opt key value. Values are validated and merged into the
"options" object of every /api/generate request.
"""

import threading


class GenOptions:
    DEFAULTS = {
        "temperature": 0.7,   # creativity 0..2
        "top_p": 0.9,         # nucleus sampling 0..1
        "max_tokens": 512,    # -> num_predict
        "num_ctx": 2048,      # context window size
        "seed": -1,           # -1 = random
    }
    KEYS = ("temperature", "top_p", "max_tokens", "num_ctx", "seed")

    def __init__(self):
        self._lock = threading.Lock()
        self.values = dict(self.DEFAULTS)

    def set(self, key, raw):
        """Parse+validate one option; returns (ok, message)."""
        if key not in self.KEYS:
            return False, f"Unknown option '{key}'. Available: {', '.join(self.KEYS)}"
        try:
            val = float(raw)
            if key in ("max_tokens", "num_ctx", "seed"):
                val = int(val)
        except ValueError:
            return False, f"Not a number: {raw!r}"
        bounds = {"temperature": (0.0, 2.0), "top_p": (0.0, 1.0),
                  "max_tokens": (1, 65536), "num_ctx": (256, 131072),
                  "seed": (-1, 2 ** 31 - 1)}[key]
        if not (bounds[0] <= val <= bounds[1]):
            return False, f"{key} must be in [{bounds[0]}, {bounds[1]}], got {val}"
        with self._lock:
            self.values[key] = val
        return True, f"{key} = {val}"

    def payload_options(self):
        """Ollama-style options dict."""
        with self._lock:
            v = dict(self.values)
        return {"temperature": v["temperature"], "top_p": v["top_p"],
                "num_predict": v["max_tokens"], "num_ctx": v["num_ctx"],
                "seed": v["seed"]}

    def summary(self):
        with self._lock:
            v = dict(self.values)
        return ", ".join(f"{k}={v[k]}" for k in self.KEYS)
