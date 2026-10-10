"""ANSI colors + startup banner for ServerCloud."""

import os

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RED = "\033[31m"


def _nocolor():
    return os.environ.get("NO_COLOR") is not None or not os.isatty(1) \
        if hasattr(os, "isatty") else False


def c(text, color):
    if _nocolor():
        return text
    return f"{color}{text}{RESET}"


LOGO = r"""
  _____         _   ____  ____  ____
 |_   _|__  ___| |_|  _ \/ ___||  _ \
   | |/ _ \/ __| __| |_) \___ \| |_) |
   | |  __/\__ \|_|  __/ ___) |  __/
   |_|\___||___/  |_|   |____/|_|      Local token factory on any hardware
"""


def banner(version: str, ollama_ok: bool, ollama_ver: str, n_models: int,
           extra=None):
    from servercloud.core.models import MODEL_CATALOG
    n = len(MODEL_CATALOG)
    lines = [c(LOGO, CYAN)]
    status = c(f"Ollama {ollama_ver} ONLINE", GREEN) if ollama_ok \
        else c("Ollama OFFLINE — run: pkg install ollama && ollama serve", RED)
    lines.append(f"  ServerCloud v{version} | {status} | downloaded models: {n_models}")
    lines.append(c("  Commands:", BOLD))
    lines += [
        "    /w [model#] [question]   ask a model (parallel OK)",
        "    /stf [tokens_per_sec]    set generation speed cap",
        "    /autt [model]            measure hardware power & auto-tune tok/s",
        f"    /models                  catalog of {n} local models (heavy >16 GB tagged)",
        "    /bmc                     BIG MODEL CATALOG: 25 GB+ giants (llama3.3:70b ... kimi-k2:1t)",
        "    /dl [catalog number]     download model (Download ...? Y/n)",
        "    /dnm [github url]        load custom model from GitHub (.gguf/Modelfile/repo)",
        "    /dnmf [local path]       load custom model from device file",
        "    /delm [name or number]   delete a downloaded model",
        "    /list                    downloaded models with numbers",
        "    /status                  live generation dashboard",
        "    /stop [job id]           stop a running job",
        "    help / quit              this list / exit",
    ]
    if extra:
        lines += list(extra)
    return "\n".join(lines)
