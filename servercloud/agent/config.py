"""Настройки и безопасное хранение GitHub-токена."""
import os
import re
from pathlib import Path

# NOTE: SERVERCLOUD_HOME is the *checkout* dir used by install scripts;
# the agent's data dir must not collide with it -> use SERVERCLOUD_DATA,
# matching servercloud_app.py (legacy TOKENPFS_* names still honoured).
HOME = Path(os.environ.get(
    "SERVERCLOUD_DATA",
    os.environ.get("TOKENPFS_DATA",
                   str(Path.home() / ".servercloud"))))
OLLAMA_URL = os.environ.get(
    "SERVERCLOUD_OLLAMA_URL",
    os.environ.get("TOKENPFS_OLLAMA_URL", "http://127.0.0.1:11434"))
DEFAULT_MODEL = os.environ.get("SERVERCLOUD_AGENT_MODEL", "qwen2.5-coder:1.5b")
NUM_CTX = int(os.environ.get("SERVERCLOUD_AGENT_NUM_CTX", "4096"))
ALLOW_PRIVATE_NET = os.environ.get("SERVERCLOUD_AGENT_ALLOW_PRIVATE", "0") == "1"

TOKEN_FILE = HOME / "github_token"
TOKEN_ENV_VARS = ("SERVERCLOUD_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN")
_TOKEN_RE = re.compile(r"(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{20,}")


def load_github_token():
    """Токен берётся из переменных окружения, затем из файла (chmod 600)."""
    for var in TOKEN_ENV_VARS:
        val = os.environ.get(var, "").strip()
        if val:
            return val
    try:
        return TOKEN_FILE.read_text().strip() or None
    except OSError:
        return None


def save_github_token(token):
    HOME.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(HOME, 0o700)
    except OSError:
        pass
    fd = os.open(str(TOKEN_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token.strip())
    os.chmod(TOKEN_FILE, 0o600)


def delete_github_token():
    try:
        TOKEN_FILE.unlink()
        return True
    except OSError:
        return False


def redact(text):
    """Вырезает токен из любого текста, который уходит модели или в лог."""
    if not text:
        return text
    tok = load_github_token()
    if tok:
        text = text.replace(tok, "***")
    return _TOKEN_RE.sub("***", text)
