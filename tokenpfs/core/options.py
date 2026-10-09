"""Generation options for Ollama (temperature, top_p, num_predict...).

Set via /opt [model] key value. Values are validated and merged into the
"options" object of every /api/generate request. Options can be set per
model (/opt 01 temperature 0.2) or as session default (/opt temperature 0.7);
a model-specific value overrides the session one.
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
    BOUNDS = {"temperature": (0.0, 2.0), "top_p": (0.0, 1.0),
              "max_tokens": (1, 65536), "num_ctx": (256, 131072),
              "seed": (-1, 2 ** 31 - 1)}

    def __init__(self):
        self._lock = threading.Lock()
        self.values = dict(self.DEFAULTS)     # session defaults
        self.per_model = {}                   # number -> {key: value}

    # ---------- helpers ----------
    def _parse(self, key, raw):
        if key not in self.KEYS:
            return None, f"Unknown option '{key}'. Available: {', '.join(self.KEYS)}"
        try:
            val = float(raw)
            if key in ("max_tokens", "num_ctx", "seed"):
                val = int(val)
        except ValueError:
            return None, f"Not a number: {raw!r}"
        lo, hi = self.BOUNDS[key]
        if not (lo <= val <= hi):
            return None, f"{key} must be in [{lo}, {hi}], got {val}"
        return val, None

    # ---------- public API ----------
    def set(self, target, key, raw=None):
        """set(key, raw) — session; set(target, key, raw) — per model."""
        if raw is None:                       # legacy call: set(key, value)
            target, key, raw = None, target, key
        val, err = self._parse(key, raw)
        if err:
            return False, err
        with self._lock:
            if target is None:
                self.values[key] = val
                scope = ""
            else:
                self.per_model.setdefault(str(target), {})[key] = val
                scope = f" (model [{target}])"
        return True, f"{key} = {val}{scope}"

    def unset(self, target, key):
        key = key.lower()
        if key not in self.KEYS:
            return False, f"Unknown option '{key}'."
        with self._lock:
            if target is None:
                self.values[key] = self.DEFAULTS[key]
                return True, f"{key} reset to default ({self.DEFAULTS[key]})."
            pm = self.per_model.get(str(target), {})
            if key in pm:
                del pm[key]
                return True, f"{key} (model [{target}]) removed; session value used."
        return False, f"{key} was not set for model [{target}]."

    def get(self, target=None, key=None):
        key = key.lower()
        if key not in self.KEYS:
            return None
        with self._lock:
            if target is not None:
                v = self.per_model.get(str(target), {}).get(key)
                if v is not None:
                    return v
            return self.values.get(key)

    def payload_options(self, target=None):
        """Ollama-style options dict, per-model overrides applied."""
        with self._lock:
            v = dict(self.values)
            if target is not None:
                v.update(self.per_model.get(str(target), {}))
        return {"temperature": v["temperature"], "top_p": v["top_p"],
                "num_predict": v["max_tokens"], "num_ctx": v["num_ctx"],
                "seed": v["seed"]}

    def summary(self, target=None):
        with self._lock:
            v = dict(self.values)
            if target is not None:
                v.update(self.per_model.get(str(target), {}))
        return ", ".join(f"{k}={v[k]}" for k in self.KEYS)
