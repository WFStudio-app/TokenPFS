"""CPTS — client for *other people's* TokenPFS network APIs.

With /cpts <SCA-key> you register a remote hoster's API key and then route
your questions there instead of (or in addition to) your local Ollama:

    /cpts SCA-XXXX-XXXX-XXXX [url]     add + activate a remote API
    /cptsm                            list all configured remotes
    /cptsuse <n> | /cptslocal         switch routing on/off
    /cptsdel <n>                      remove a remote

The remote speaks the same protocol as tokenpfs/modules/api_server.py:
  GET  /api/health            -> {"ok":true,"app":"TokenPFS",...}
  GET  /v1/models             -> {"models":[...]}          (Bearer key)
  POST /v1/chat               -> {"response":"..."}       (Bearer key)
Auth header: Authorization: Bearer SCA-XXXX-XXXX-XXXX
Standard library only — works on Termux/Linux/Windows/macOS.
"""

import json
import os
import re
import urllib.error
import urllib.request

KEY_RE = re.compile(r"^SCA-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$")


def validate_key(key: str) -> bool:
    """Strict check of the SCA-XXXX-XXXX-XXXX format."""
    return bool(KEY_RE.match(key.strip().upper()))


class CptsStore:
    """Persistent list of remote TokenPFS API endpoints."""

    def __init__(self, path):
        self.path = path
        self.remotes = {}      # slot(str) -> dict
        self.active = None     # slot currently routed to, or None (=local)
        self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self.remotes = data.get("remotes", {})
            self.active = data.get("active")
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self.remotes, self.active = {}, None

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"remotes": self.remotes, "active": self.active},
                      f, indent=2)
        os.replace(tmp, self.path)

    # ---------- CRUD ----------
    def add(self, url, key):
        slot = str(max((int(s) for s in self.remotes), default=0) + 1)
        self.remotes[slot] = {
            "url": url.rstrip("/"),
            "key": key,
            "added": _now(),
            "last_status": "-",
            "calls_ok": 0,
            "calls_fail": 0,
        }
        self.save()
        return slot, self.remotes[slot]

    def get(self, slot):
        return self.remotes.get(str(slot))

    def remove(self, slot):
        slot = str(slot)
        r = self.remotes.pop(slot, None)
        if r and self.active == slot:
            self.active = None
        self.save()
        return r

    def set_active(self, slot):
        slot = str(slot)
        if slot not in self.remotes:
            return False
        self.active = slot
        self.save()
        return True

    def deactivate(self):
        self.active = None
        self.save()

    def all(self):
        return dict(self.remotes)


def _now():
    import time
    return time.strftime("%Y-%m-%d %H:%M")


class CptsClient:
    """Minimal HTTP client for a remote TokenPFS API."""

    def __init__(self, url, key, timeout=120):
        self.url = url.rstrip("/")
        self.key = key.strip().upper()
        self.timeout = timeout

    def _headers(self):
        return {"Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json"}

    def _get(self, path, timeout=None):
        req = urllib.request.Request(self.url + path, headers=self._headers())
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
            return json.loads(r.read().decode(errors="replace"))

    def _post(self, path, payload, timeout=None):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(self.url + path, data=data,
                                     headers=self._headers(), method="POST")
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as r:
            return json.loads(r.read().decode(errors="replace"))

    # ---------- public API ----------
    def health(self):
        """Ping without auth — verifies it is really a TokenPFS API."""
        info = self._get("/api/health", timeout=10)
        return info

    def models(self):
        return self._get("/v1/models", timeout=15).get("models", [])

    def chat(self, model_ref, prompt, options=None):
        """Send one question; returns the answer text (raises on error)."""
        resp = self._post("/v1/chat",
                          {"model": model_ref,
                           "messages": [{"role": "user", "content": prompt}],
                           "options": options or {}})
        return resp.get("response", "")
