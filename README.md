# TokenPFS ⚡

**Local token factory — run 20 local LLMs on any hardware via Ollama. Built for Termux.**

Generate tokens locally, ask several models **in parallel**, watch live generation stats, pay nothing for API calls.

[![Version](https://img.shields.io/badge/version-1.0.0-blue)]() [![Python](https://img.shields.io/badge/python-3.6+-green)]() [![Platform](https://img.shields.io/badge/platform-Termux%20%7C%20Linux-orange)]() [![Engine](https://img.shields.io/badge/engine-Ollama-purple)]()

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **20 local models** | Curated catalog of small/medium LLMs (Llama, Qwen, Phi, Gemma, DeepSeek…) sized 0.4–4.7 GB |
| 🔢 **Model numbering** | Every downloaded model gets a number right after install: `[01]`, `[02]`, … |
| ⚙️ **Ollama engine** | Real inference through the Ollama HTTP API (`ollama serve`) — or remote host via `TOKENPFS_OLLAMA_URL` |
| 🪟 **Download confirm** | `Download [model]? Y/n` + live progress bar while pulling weights |
| 🚄 **Parallel chat** | Ask model A and model B at the same time — separate worker threads |
| 📊 **Live dashboard** | While generating you see: `Text — [model] [what it does now] [tok/s] [ready in Ns]` |
| 💬 **Clean answers** | Final line format: `> [model] - [answer] [time] [consumed tokens]` |
| 🎛️ **Speed control** | `/stf <N>` sets how many tokens per second are produced for an answer |
| 🧪 **Demo mode** | If Ollama is offline, everything still runs in simulated mode so you can learn the UX |

---

## 🚀 Quick start (Termux)

```bash
pkg update && pkg upgrade
pkg install python ollama git
git clone https://github.com/WFStudio-app/TokenPFS.git
cd TokenPFS

# start the inference server (keep it running)
ollama serve &

# start TokenPFS
python3 tokenpfs_app.py
```

### Typical session

```text
tokenpfs> /models            # show the catalog of 20 models
tokenpfs> /dl 2              # pick catalog №2 → Download [qwen2.5:0.5b]? Y/n
   downloading qwen2.5:0.5b: [########                  ]  32.4%
Model ready: [01] qwen2.5:0.5b     ← number assigned right after download!

tokenpfs> /dl 1
Download [llama3.2:1b]? Y n… y
Model ready: [02] llama3.2:1b

tokenpfs> /stf 15            # generate ~15 tokens per second

tokenpfs> /w 01 What is a MAC address?
Job #1 started → [01] qwen2.5:0.5b @ 15.0 tok/s
tokenpfs> /w 02 Explain NAT briefly
Job #2 started → [02] llama3.2:1b @ 15.0 tok/s

  ⚙ [qwen2.5:0.5b] [generating (48 tok)] [14.9 tok/s] [ready in 31s]
  ⚙ [llama3.2:1b]  [generating (41 tok)] [15.1 tok/s] [ready in 28s]

> [llama3.2:1b] - NAT rewrites private IPs to public ones… [34.2s] [512 tok]
> [qwen2.5:0.5b] - A MAC address is a unique hardware ID… [36.8s] [512 tok]
```

Both questions were generated **in parallel**.

---

## 🖥️ Command reference

| Command | What it does |
|---|---|
| `/models` | Catalog of 20 available local models with sizes |
| `/dl <catalog №>` | Download a model (`Download [name]? Y/n`), assigns `[NN]` number |
| `/list` | Downloaded models with their numbers |
| `/w <model/name> <question>` | Ask a question; multiple jobs run in parallel |
| `/stf <tokens_per_sec>` | Set generation speed (0.1–1000 tok/s) |
| `/status` | Snapshot of all active generations |
| `/stop <job id>` | Stop a running job |
| `help` / `quit` | Command list / exit (waits for running jobs up to 60 s) |

Environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `TOKENPFS_OLLAMA_URL` | `http://127.0.0.1:11434` | Point to a local or remote Ollama server |
| `TOKENPFS_HOME` | `~/.tokenpfs` | Where the numbered-model registry is stored |
| `NO_COLOR` | – | Disable ANSI colors |

---

## 🗂️ Project structure

```
TokenPFS/
├── tokenpfs_app.py           # entry point (REPL + live dashboard thread)
└── tokenpfs/
    ├── core/
    │   ├── version.py        # X.X.X versioning algorithm + bump()
    │   ├── models.py         # catalog of 20 local models
    │   ├── registry.py       # [01],[02]... numbering after download
    │   └── jobs.py           # parallel generation manager + status lines
    ├── modules/
    │   └── ollama_api.py     # Ollama HTTP client (pull/generate/tags)
    └── utils/
        └── colors.py         # ANSI colors + startup banner
```

---

## 🔢 Versioning algorithm

| Format | Type | Meaning |
|---|---|---|
| `X.0.0` | 🌋 Global | full rewrite, breaking changes |
| `0.X.0` | 🚀 Major | big new features |
| `0.0.X` | 🔧 Mini | fixes and tweaks |

---

## ❓ FAQ

**Is this legal / free?** Yes — Ollama runs open-weight models entirely on your device; no cloud, no API keys.

**Why "demo mode"?** If `ollama serve` isn't running, TokenPFS simulates generation so you can try the interface. Start Ollama for real answers.

**Which model should I pick on a phone?** `qwen2.5:0.5b` (~0.4 GB) or `tinyllama:1.1b` — fastest on Termux.

**Can I use a PC as the engine from my phone?** Yes: run Ollama on the PC, then `export TOKENPFS_OLLAMA_URL=http://PC_IP:11434`.

---

## ⚠️ Hardware notes

* Small phones (<4 GB RAM): only ≤1.5 B models.
* 6–8 GB devices: 3–4 B models OK.
* Generation speed depends on your CPU/NPU; `/stf` caps output rate, it cannot make hardware faster than it is.

---

## 📄 License

MIT — see [LICENSE](LICENSE).
