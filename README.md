# TokenPFS ⚡

**Local token factory — run 20 local LLMs on any hardware via Ollama. Built for Termux.**

Generate tokens locally, ask several models **in parallel**, watch live generation stats, pay nothing for API calls.

[![Version](https://img.shields.io/badge/version/2.00.2--API.Beta.0-blue)]() [![Python](https://img.shields.io/badge/python-3.6+-green)]() [![Platform](https://img.shields.io/badge/platform-Termux%20%7C%20Linux-orange)]() [![Engine](https://img.shields.io/badge/engine-Ollama-purple)]()

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 **90 local models** | Small → frontier class (Llama, Qwen, Phi, Gemma, DeepSeek…), 0.4 GB … 594 GB; `/bmc` shows 25 GB+ giants |
| 🔢 **Model numbering** | Every downloaded model gets a number right after install: `[01]`, `[02]`, … |
| ⚙️ **Ollama engine** | Real inference through the Ollama HTTP API (`ollama serve`) — or remote host via `TOKENPFS_OLLAMA_URL` |
| 🪟 **Download confirm** | `Download [model]? Y/n` + live progress bar while pulling weights |
| 🚄 **Parallel chat** | Ask model A and model B at the same time — separate worker threads |
| 📊 **Live dashboard** | While generating you see: `Text — [model] [what it does now] [tok/s] [ready in Ns]` |
| 💬 **Clean answers** | Final line format: `> [model] - [answer] [time] [consumed tokens]` |
| 🎛️ **Speed control** | `/stf <N>` sets how many tokens per second are produced for an answer |
| 🧪 **Demo mode** | If Ollama is offline, everything still runs in simulated mode so you can learn the UX |
| 🌐 **Network API** | `/apis` — host your local models over HTTP with `SCA-XXXX-XXXX-XXXX` keys, model whitelists, history toggle & rate limits |
| 📡 **Remote APIs as engine** | `/cpts <SCA-key>` — use *someone else's* TokenPFS API as your generation backend; switch between remotes and back to local anytime |

---

## ⚡ One-click install (recommended)

Auto-installer for **Linux, Termux, macOS and VPS/cloud servers** (headless over SSH): detects your package manager (apt/dnf/yum/pacman/zypper/apk), installs Python/Git/Ollama, clones the repo and creates a `tokenpfs` command:

```bash
curl -fsSL https://raw.githubusercontent.com/WFStudio-app/TokenPFS/main/scripts/install.sh | bash
# then open a new terminal and run:
tokenpfs
```

**Windows 10/11** — in PowerShell:

```powershell
iwr -useb https://raw.githubusercontent.com/WFStudio-app/TokenPFS/main/scripts/install.ps1 | iex
# reopen the terminal and run:
tokenpfs
```

**VPS / cloud server** — same Linux one-liner works over SSH as root (`ssh root@your-vps` → paste command). `/autt` inside TokenPFS shows detected platform and virtualization class.

## 🚀 Manual quick start (Termux)

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
tokenpfs> /models            # show the catalog of 90 models
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
| `/models` | Catalog of 90 available local models with sizes |
| `/dl <catalog №>` | Download a model (`Download [name]? Y/n`), assigns `[NN]` number |
| `/list` | Downloaded models with their numbers |
| `/w <model/name> <question>` | Ask a question; multiple jobs run in parallel |
| `/stf <tokens_per_sec>` | Set generation speed (0.1–1000 tok/s) |
| `/status` | Snapshot of all active generations |
| `/stop <job id>` | Stop a running job |
| `/apis <models> <Y/N> <req/min> <slot#>` | Create an API key & host models over the network (see below) |
| `/apim` | List/monitor your API keys and server status |
| `/apioff <slot#>` / `/apion <slot#>` | Disable / re-enable one API key |
| `/apidel <slot#>` | Delete an API key |
| `/cpts <SCA-key> [url]` | Add a **remote** TokenPFS API (someone else's host) and route your questions through it |
| `/cptsm` | List configured remote APIs + active routing |
| `/cptsuse <n>` / `/cptslocal` | Switch routing to remote #n / back to local models |
| `/cptsdel <n>` | Remove a remote API |
| `help` / `quit` | Command list / exit (waits for running jobs up to 60 s) |

---

## 🌐 Network API — host your local models (`/apis`)

TokenPFS can expose selected local models over HTTP so **other devices on your
LAN/WAN can query them** using per-key authentication, model whitelists,
optional dialog-history access and a requests-per-minute cap.

### Create a key

```
tokenpfs> /apis 01,02,03 Y 60 1
API key #1 created:
   Key        : SCA-ABCD-EFGH-JKMN
   Models     : 01, 02, 03      <- only these numbers are reachable via this key
   History    : allowed         <- Y = client may read chat history (N = not)
   Rate limit : 60 req/min
   Endpoint   : http://192.168.x.x:8777
```

Format: `/apis [model numbers через запятую] [Y/N доступ к истории] [макс. запросов в минуту] [номер ключа]`.
The key itself is generated automatically in the documented shape **`SCA-XXXX-XXXX-XXXX`**
(crypto-random, unambiguous alphabet); the *slot number* is the one you choose.

### Manage keys

- `/apim` — table of all keys (on/off, models, rpm, served count)
- `/apioff 1` — instantly disable key #1 (clients get `401 api key disabled`)
- `/apion 1` — enable it again
- `/apidel 1` — remove it permanently

### Endpoints (all JSON, auth via `Authorization: Bearer SCA-...` or `X-API-Key`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | liveness check (no auth) |
| GET | `/v1/models` | models bound to your key |
| POST | `/v1/chat` | `{"model":"01","messages":[{"role":"user","content":"Привет"}]}` |
| POST | `/v1/generate` | `{"model":"01","prompt":"..."}` |
| GET | `/v1/history?model=01` | dialog history — **only if key was created with `Y`** |

Optional per-request generation overrides: `temperature`, `top_p`, `max_tokens`, `num_ctx`, `seed`.

Errors: `401` bad/disabled key · `403` model not bound to key / history denied ·
`404` model unavailable on host · `429` rate limit exceeded · `502` generation failed.

### Client example

```bash
curl -X POST http://YOUR-HOST:8777/v1/chat \
  -H "Authorization: Bearer SCA-ABCD-EFGH-JKMN" \
  -H "Content-Type: application/json" \
  -d '{"model":"01","messages":[{"role":"user","content":"Привет!"}]}'
```

Server address/port: env `TOKENPFS_API_HOST` (default `0.0.0.0`) and
`TOKENPFS_API_PORT` (default `8777`). Keys persist in `~/.tokenpfs/api_keys.json`.
⚠️ The API is plain HTTP — intended for trusted LANs; put it behind SSH tunnel /
reverse-proxy with TLS for public exposure.

Environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `TOKENPFS_OLLAMA_URL` | `http://127.0.0.1:11434` | Point to a local or remote Ollama server |
| `TOKENPFS_HOME` | `~/.tokenpfs` | Where the numbered-model registry is stored |
| `NO_COLOR` | – | Disable ANSI colors |

---

## 📡 Remote APIs as your engine — `/cpts` (Call People's TokenPFS Servers)

The flip side of `/apis`: if **another person** hosts TokenPFS and gave you a
key (`SCA-XXXX-XXXX-XXXX`), you can use *their* models as if they were yours —
no download, no hardware needed on your side.

```
tokenpfs> /cpts SCA-ABCD-EFGH-JKMN http://192.168.1.40:8777
Remote API #1 added and ACTIVATED:
   URL      : http://192.168.1.40:8777
   Key      : SCA-ABCD-EFGH-JKMN
   Server   : TokenPFS 2.0.2-API.Beta.0
   Models   : qwen2.5:0.5b, llama3.2:1b
From now on /w questions go through this remote API. Switch back to local models with /cptslocal.
```

What happens under the hood:

- On `/cpts` TokenPFS **verifies before saving**: pings `/api/health` (must be
  a real TokenPFS server), then checks the key against `/v1/models`
  (bad/disabled key → `401`, never saved). Only a working pair gets stored.
- Every `/w <model> <question>` is then sent as `POST /v1/chat` with your
  Bearer key; the answer streams into the normal dashboard/result format.
  The hoster's model whitelist and rate limit apply automatically.
- Remotes persist in `~/.tokenpfs/cpts.json` together with per-remote call
  statistics (`ok/fail/last status` — visible in `/cptsm`).

Management commands:

| Command | Effect |
|---|---|
| `/cptsm` | list all remotes, mark the active one `[>>]`, show counters |
| `/cptsuse 2` | route through remote #2 |
| `/cptslocal` | stop routing — back to your own Ollama/demo |
| `/cptsdel 1` | delete remote #1 (active slot falls back to local) |

Chaining works too: a host that itself has an active `/cpts` remote forwards
incoming `/v1/chat` requests upstream, so A→B→C relay chains are possible.

⚠️ Your question text leaves your machine to the remote host — only add keys
from people/servers you trust. HTTP traffic is unencrypted by default; ask
large providers for TLS or use an SSH tunnel.

---

## 🗂️ Project structure

```
TokenPFS/
├── tokenpfs_app.py           # entry point (REPL + live dashboard thread)
└── tokenpfs/
    ├── core/
    │   ├── version.py        # X.X.X versioning algorithm + bump()
    │   ├── models.py         # catalog of 90 local models (incl. 25 GB+ giants)
    │   ├── registry.py       # [01],[02]... numbering after download
    │   └── jobs.py           # parallel generation manager + status lines
    ├── modules/
    │   ├── ollama_api.py     # Ollama HTTP client (pull/generate/tags)
    │   ├── api_server.py     # /apis — host local models over HTTP (SCA keys)
    │   └── cpts_api.py       # /cpts — client for remote TokenPFS APIs
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

## v1.1.0 additions
- **90-model catalog** (was 42; see v2.1.1 for the giant class + /bmc) — now includes heavy class (>16 GB SSD): `llama3.1:70b`, `mixtral:8x22b`, `mistral-large`, `qwen2.5:32b`, `deepseek-r1:32b` and more, tagged `[HEAVY >16GB]` with automatic disk-space check before download.
- **`/autt [model]`** — measures hardware power (CPU cores, load, RAM, SSD, SoC temp → POWER SCORE 0–100) and auto-recommends `/stf` tokens-per-second tuned to your device.
- **`/dnm <github-url>`** — load custom models from GitHub: direct `.gguf`/Modelfile raw link, blob link (auto-converted), or a plain repo URL (README is scanned for model links). Registered in Ollama when online, numbered `[NN]` right after.
- **`/dnmf <path>`** — load your own local `.gguf` / Modelfile from the device.
- **`/delm <name or number>`** — delete a downloaded model (registry + `ollama rm`).
