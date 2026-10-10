"""Custom model loading: /dnm (GitHub URL) and /dnmf (local file).

Supported sources:
  * GitHub blob/raw link to a *.gguf or a Modelfile
  * github.com/<owner>/<repo>            -> scans README for gguf links
  * HuggingFace resolve URLs             -> converted to direct raw
Local files: *.gguf or Modelfile.

If Ollama is online the model is registered via a generated Modelfile
(ollama create). Offline it is registered in ServerCloud registry only
(demo mode), so numbering [NN] still works.
"""

import os
import re
import json
import urllib.request
import urllib.error

USER_AGENT = "Mozilla/5.0 (ServerCloud)"


def _http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return f.read()


def normalize_github_url(url: str):
    """Convert a GitHub page link to its raw form; HF resolve -> raw."""
    url = url.strip()
    # huggingface resolve link
    if "huggingface.co" in url and "/resolve/" in url:
        return url  # already direct download link
    m = re.match(r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/blob/(.+)", url)
    if m:
        owner, repo, rest = m.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{rest}"
    m = re.match(r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$", url)
    if m:
        return url  # plain repo — handled by scan_repo_readme
    return url


def name_from_url(url: str):
    base = url.rstrip("/").split("/")[-1].split("?")[0]
    base = re.sub(r"\.gguf$|\.bin$|Modelfile.*$", "", base, flags=re.I)
    base = re.sub(r"[^A-Za-z0-9._-]", "-", base) or "custom-model"
    return f"custom/{base.lower()}:latest"


def scan_repo_readme(owner: str, repo: str):
    """Return list of gguf/Modelfile URLs found in the repo README."""
    found = []
    for branch in ("main", "master"):
        for fname in ("README.md", "readme.md", "README.rst"):
            try:
                raw = _http_get(
                    f"https://raw.githubusercontent.com/{owner}/{repo}/"
                    f"{branch}/{fname}").decode("utf-8", "replace")
            except Exception:
                continue
            links = re.findall(
                r"https?://[^\s)\]]+\.(?:gguf|bin)(?:\?[^\s)\]]*)?"
                r"|https?://huggingface\.co/[^\s)\]]+/resolve/[^\s)\]]+", raw)
            found.extend(dict.fromkeys(links))
            if found:
                return found
        if found:
            break
    return found


def fetch_file_to(url: str, dest_dir: str):
    """Download url into dest_dir; returns local path."""
    os.makedirs(dest_dir, exist_ok=True)
    fname = url.rstrip("/").split("/")[-1].split("?")[0] or "download.bin"
    fname = re.sub(r"[^A-Za-z0-9._-]", "_", fname)
    dest = os.path.join(dest_dir, fname)
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as src, open(tmp, "wb") as out:
        total = int(src.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = src.read(65536)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                pct = 100 * done / total
                bar = "#" * int(pct // 4)
                print(f"\r  fetching: [{bar:<25}] {pct:5.1f}% ({done//1024} KB)",
                      end="", flush=True)
    print()
    os.replace(tmp, dest)
    return dest


def size_gb(path: str) -> float:
    try:
        return round(os.path.getsize(path) / (1024 ** 3), 2)
    except OSError:
        return 0.0


def make_modelfile(gguf_path: str, adapter_path=None):
    lines = [f'FROM {os.path.abspath(gguf_path)}']
    if adapter_path:
        lines.append(f'ADAPTER {os.path.abspath(adapter_path)}')
    return "\n".join(lines) + "\n"


def register_with_ollama(modelfile_path: str, model_name: str):
    """Run `ollama create -f` if available; return True on success."""
    import subprocess
    try:
        r = subprocess.run(["ollama", "create", model_name, "-f", modelfile_path],
                           capture_output=True, text=True, timeout=600)
        return r.returncode == 0
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return False
