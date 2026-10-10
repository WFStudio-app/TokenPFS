"""Hugging Face integration: search, GGUF download and dataset access.

All functions use only the Python standard library (urllib), so this works
on Termux / Linux / Windows / macOS without installing `huggingface_hub`.

Endpoints used:
  * https://huggingface.co/api/models?search=...&pipeline_tag=text-generation
  * https://huggingface.co/api/models/<repo>/tree/main (file listing)
  * https://huggingface.co/<repo>/resolve/<path>       (raw file download)
  * https://huggingface.co/api/datasets?search=...     (dataset database)
  * https://huggingface.co/datasets/<repo>/resolve/... (dataset files)

Private / gated repos need a token: set env SERVERCLOUD_HF_TOKEN or pass it
explicitly (it is sent as `Authorization: Bearer <hf_token>`).
"""

import os
import re
import json
import urllib.request
import urllib.error
import urllib.parse

HF_BASE = "https://huggingface.co"
USER_AGENT = "Mozilla/5.0 (ServerCloud)"


class HFError(Exception):
    pass


def _token():
    return os.environ.get("SERVERCLOUD_HF_TOKEN", "").strip()


def _http_get(url, timeout=25, binary=False):
    headers = {"User-Agent": USER_AGENT}
    tok = _token()
    if tok and HF_BASE in url:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as f:
        data = f.read()
    return data if binary else data.decode("utf-8", "replace")


def _http_json(url, timeout=25):
    try:
        return json.loads(_http_get(url, timeout))
    except urllib.error.HTTPError as e:
        raise HFError(f"HTTP {e.code} from Hugging Face ({url.split('?')[0]})")
    except Exception as e:
        raise HFError(f"Hugging Face request failed: {e}")


# ---------------------------------------------------------------- search ---

def search_models(query: str, limit: int = 15):
    """Search text-generation models on HF. Returns list of dicts."""
    q = urllib.parse.quote(query.strip())
    url = (f"{HF_BASE}/api/models?search={q}&pipeline_tag=text-generation"
           f"&sort=downloads&direction=-1&limit={int(limit)}")
    items = _http_json(url)
    out = []
    for m in items:
        out.append({
            "id": m.get("modelId") or m.get("id", "?"),
            "downloads": m.get("downloads", 0),
            "likes": m.get("likes", 0),
            "gated": bool(m.get("gated")),
        })
    return out


def search_datasets(query: str, limit: int = 15):
    """Search datasets (the HF 'database') by name."""
    q = urllib.parse.quote(query.strip())
    url = f"{HF_BASE}/api/datasets?search={q}&sort=downloads&direction=-1&limit={int(limit)}"
    items = _http_json(url)
    out = []
    for d in items:
        out.append({
            "id": d.get("id", "?"),
            "downloads": d.get("downloads", 0),
            "likes": d.get("likes", 0),
            "gated": bool(d.get("gated")),
        })
    return out


# ------------------------------------------------------------- repo tree ---

def list_gguf_files(repo_id: str):
    """Return [(filename, size_bytes)] of .gguf files in a model repo.

    Multi-part GGUFs (file-00001-of-00002.gguf) are summed into one entry so
    the reported size is the real full-model weight."""
    files = []
    cursor = None
    while True:
        url = f"{HF_BASE}/api/models/{urllib.parse.quote(repo_id)}/tree/main?recursive=true"
        if cursor:
            url += f"&cursor={urllib.parse.quote(cursor)}"
        data = _http_json(url)
        if isinstance(data, dict):          # paginated form
            entries = data.get("entries", [])
            cursor = data.get("nextCursor")
        else:
            entries, cursor = data, None
        for e in entries:
            path = e.get("path", "")
            if path.lower().endswith(".gguf"):
                files.append((path, e.get("size", 0) or 0))
        if not cursor:
            break
    # merge multi-part shards: qwen-q4_k_m-00001-of-00003.gguf -> qwen-q4_k_m.gguf
    merged = {}
    order = []
    part_re = re.compile(r"-\d{5}-of-\d{5}(?=\.gguf$)", re.I)
    for path, size in files:
        key = part_re.sub("", path)
        if key not in merged:
            merged[key] = 0
            order.append(key)
        merged[key] += size
    return [(p, merged[p]) for p in order]


def list_repo_files(repo_id: str, is_dataset: bool = False):
    """Return [(path, size_bytes)] of all files in a model/dataset repo."""
    kind = "datasets" if is_dataset else "models"
    url = (f"{HF_BASE}/api/{kind}/{urllib.parse.quote(repo_id)}"
           f"/tree/main?recursive=true")
    data = _http_json(url)
    entries = data.get("entries", data) if isinstance(data, dict) else data
    out = []
    for e in entries:
        if isinstance(e, dict) and e.get("type") == "file":
            out.append((e.get("path", "?"), e.get("size", 0) or 0))
    return out


# ------------------------------------------------------------ download ---

def gguf_download_url(repo_id: str, filename: str):
    return f"{HF_BASE}/{repo_id}/resolve/main/{filename}"


def fetch_file_to(url: str, dest_dir: str, progress=True):
    """Stream a remote file into dest_dir; returns local path."""
    os.makedirs(dest_dir, exist_ok=True)
    fname = url.rstrip("/").split("/")[-1].split("?")[0] or "download.bin"
    fname = re.sub(r"[^A-Za-z0-9._-]", "_", fname)
    dest = os.path.join(dest_dir, fname)
    tmp = dest + ".part"
    headers = {"User-Agent": USER_AGENT}
    tok = _token()
    if tok and HF_BASE in url:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as src, open(tmp, "wb") as out:
            total = int(src.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = src.read(65536)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if progress and total:
                    pct = 100 * done / total
                    bar = "#" * int(pct // 4)
                    print(f"\r  downloading: [{bar:<25}] {pct:5.1f}% "
                          f"({done // 1048576} MB/{total // 1048576} MB)",
                          end="", flush=True)
        if progress and total:
            print()
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise HFError(
                "Access denied (HTTP %d). The repo is gated/private: accept its "
                "license on huggingface.co and set SERVERCLOUD_HF_TOKEN." % e.code)
        raise HFError(f"HTTP {e.code} while downloading {url}")
    except OSError as e:
        raise HFError(f"Network error: {e}")
    os.replace(tmp, dest)
    return dest


def size_gb(path: str) -> float:
    try:
        return round(os.path.getsize(path) / (1024 ** 3), 2)
    except OSError:
        return 0.0


def name_from_repo(repo_id: str, filename: str):
    """Ollama-friendly model name from an HF repo + file."""
    base = os.path.splitext(os.path.basename(filename))[0]
    base = re.sub(r"[^A-Za-z0-9._-]", "-", base).lower()
    short = repo_id.split("/")[-1]
    short = re.sub(r"[^A-Za-z0-9._-]", "-", short).lower()
    return f"hf/{short}-{base}:latest"


def make_modelfile(gguf_path: str):
    return f"FROM {os.path.abspath(gguf_path)}\n"


def register_with_ollama(modelfile_path: str, model_name: str):
    import subprocess
    try:
        r = subprocess.run(["ollama", "create", model_name, "-f", modelfile_path],
                           capture_output=True, text=True, timeout=1800)
        return r.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
