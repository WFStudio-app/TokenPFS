"""Ollama HTTP client (works on Termux via pkg install ollama / or remote host).

Uses only the standard library. Base URL configurable through env
TOKENPFS_OLLAMA_URL (default http://127.0.0.1:11434).
"""

import json
import os
import urllib.request
import urllib.error

DEFAULT_URL = "http://127.0.0.1:11434"


def base_url() -> str:
    return os.environ.get("TOKENPFS_OLLAMA_URL", DEFAULT_URL).rstrip("/")


def _request(path: str, payload=None, timeout=30):
    url = base_url() + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp


def is_alive() -> bool:
    try:
        with _request("/api/version", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def server_version() -> str:
    try:
        with _request("/api/version", timeout=5) as r:
            return json.loads(r.read().decode()).get("version", "?")
    except Exception:
        return "?"


def list_local_models():
    """Return names of models already pulled into the Ollama library."""
    try:
        with _request("/api/tags", timeout=10) as r:
            data = json.loads(r.read().decode())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def pull_model(name: str, on_progress=None, timeout=3600):
    """Download a model; call on_progress(dict) with status lines.

    Returns True on success.
    """
    try:
        with _request("/api/pull", {"name": name, "stream": True},
                      timeout=timeout) as resp:
            done = False
            for raw in resp:
                line = raw.decode(errors="replace").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if on_progress:
                    on_progress(obj)
                if obj.get("status", "").lower() in ("success", "already exists"):
                    done = True
                if "error" in obj:
                    return False
            return done
    except Exception:
        return False


def generate_stream(model: str, prompt: str, tokens_per_sec: float,
                    on_token=None, stop_flag=None, timeout=600):
    """Generate an answer token-by-token, throttled to ~tokens_per_sec.

    Returns (full_text, n_tokens, elapsed_seconds) or raises.
    Throttling simulates the requested tps rate on top of real generation.
    """
    import time
    payload = {"model": model, "prompt": prompt, "stream": True,
               "options": {"num_predict": 512}}
    text_parts = []
    n_tok = 0
    start = time.time()
    with _request("/api/generate", payload, timeout=timeout) as resp:
        period = 1.0 / max(tokens_per_sec, 0.1)
        next_emit = time.time()
        for raw in resp:
            if stop_flag is not None and stop_flag.is_set():
                break
            line = raw.decode(errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            tok = obj.get("response", "")
            if tok:
                # throttle to requested tokens/sec
                wait = next_emit - time.time()
                if wait > 0:
                    time.sleep(wait)
                next_emit = max(next_emit + period, time.time())
                text_parts.append(tok)
                n_tok += 1
                if on_token:
                    on_token(tok)
            if obj.get("done"):
                stats = obj.get("eval_count")
                if isinstance(stats, int) and stats > 0:
                    n_tok = max(n_tok, 0)  # keep streamed count
                break
    return "".join(text_parts), n_tok, time.time() - start
