## [Unreleased] — catalog GLM + Gemini sweep (120 → 135 models)

- **Catalog expanded 120 → 135 models**: GLM family additions (`glm4v:9b`, `glm-4:9b-0414`, `glm-4-alltools:32b`, `glm-4-0416:32b`, `chatglm3:6b`, `chatglm:6b-v2`, `glm-4.7:cloudless`) and Google Gemini/Gemma open-weight line (`gemma3n:e4b`, `gemma2:9b/27b`, `gemma3:12b`, `shieldgemma:2b`, `embedgemma:300m`, `gemini-2.0-flash:cloudless`, `gemini-2.5-pro:cloudless`). Duplicate entries removed; `/apis` validation range now 01..135.

## [Unreleased] — catalog Qwen sweep (90 → 120 models)

- **Catalog expanded 90 → 120 models**: full Qwen family sweep — Qwen 1.0 (`qwen:7b/14b/32b/72b`), Qwen2 (`0.5b/1.5b/7b/72b`), Qwen2.5 gaps (`1.5b`, `14b`), coders (`coder:1.5b/7b/14b/next:80b`), vision-language (`vl:3b/7b/32b/72b`, `qwen3-vl:8b`), math (`math:1.5b/7b/72b`), `qwq:32b-preview`, Qwen3 (`1.7b/14b/30b-a3b/32b/coder:30b-a3b/coder:480b-a35b/max:cloudless`). `/bmc` now lists 24 giants incl. `qwen3-coder:480b-a35b`.

## [Unreleased]

### Added
- **Catalog expanded 71 → 90 models**: full Mistral sweep (`mistral:7b-instruct-v0.2/v0.3`, `mistral-nemo`, `mistral-small3.2:24b`, `mistral-large:2`, `pixtral:12b`, `magistral:7b`, `devstral-small:24b`) and full DeepSeek sweep (`deepseek-llm:7b`, `deepseek-coder:1.3b/6.7b/33b`, `deepseek-coder-v2:16b`, `deepseek-r1:8b/14b/distill-qwen-1.5b`, `deepseek-v2:16b`, `deepseek-r1:671b`). `/bmc` now lists 18 giants incl. `deepseek-r1:671b`.

## [2.00.2-API.Beta.0] — 2026-10-10 (Network API)

### Added
- **Remote APIs as engine (`/cpts`)**: `/cpts <SCA-key> [url]` registers *another person's* ServerCloud host after live verification (`/api/health` + key check via `/v1/models` — bad keys are never saved), then all `/w` questions route through `POST /v1/chat` of that host. Manage with `/cptsm` (list + ok/fail counters), `/cptsuse <n>`, `/cptslocal`, `/cptsdel <n>`. Remotes persist in `~/.servercloud/cpts.json`. Relay chains A→B→C supported (a host with an active remote forwards incoming API requests upstream). New module `servercloud/modules/cpts_api.py`; README section «📡 Remote APIs as your engine».
- **Network API**: `/apis <models> <Y/N hist> <req/min> <slot#>` creates an `SCA-XXXX-XXXX-XXXX` key and hosts the chosen models over HTTP (auto-start on :8777, `TOKENPFS_API_HOST/PORT`). Endpoints: `/api/health`, `/v1/models`, `/v1/chat`, `/v1/generate`, `/v1/history?model=NN` (Y-keys only). Per-request temperature/top_p/max_tokens/num_ctx/seed overrides; proper 401/403/404/429/502 codes.
- Key management: `/apim` monitor table, `/apioff <#>` / `/apion <#>` instant enable/disable, `/apidel <#>` delete. Keys persist in `~/.servercloud/api_keys.json`. README + banner + help updated.

### Fixed
- `/opt 01 temperature` (documented form) no longer "Unknown option '01'"; dispatch rewritten.
- `/stop` keeps only the visible text in history (tagged `[stopped by user]`) instead of leaking the full hidden generation.
- `pull_model()` false "Download failed" fixed for Ollama builds without a final success line.
- REPL prefix collisions gone (`/watson …` ≠ `/w`, `/dlsx` ≠ `/dl sx`).
- Tests use temp chat stores — no more writes into real `~/.servercloud/chat.json`.
- `TOKENPFS_HOME` (installer checkout) vs `TOKENPFS_DATA` (app data) can no longer collide.
- API model refs accept "01"/"1" interchangeably.

### [2.1.1-alpha] — 2026-10-10 (Unreleased)

### Added
- **Catalog expanded 42 → 71 models**: new light/mid class (qwen3:0.6b/4b/8b, gemma3n:e2b, granite4:micro, minimax-m2:cloudless, ernie4.5:0.3b, lfm2:1.2b, nemotron-mini:4b, exaone4:7.8b) and giant class (llama3.3:70b, qwen2.5:72b, deepseek-r1:70b, gpt-oss:120b, command-r-plus, llama3.1:405b, deepseek-v3:671b, kimi-k2:1t…).
- **`/bmc` — Big Model Catalog**: only models needing ≥25 GB free SSD, sorted by size with hardware-class tags (single server GPU / multi-GPU server / datacenter). Magenta output, tip to check disk via `/autt`.
- `/models` header now advertises `/bmc`; `help` lists `/bmc`; banner shows the new command.

 Changelog — ServerCloud

Version algorithm (X.X.X): **X.0.0** global · **0.X.0** major · **0.0.X** mini

## Unreleased — chat & generation upgrade (will be the next release)
- **Chat context**: `/w` is now a real conversation — system prompt + full per-model history (ChatML) sent to Ollama; assistant turns stored automatically. `/clear [model]` resets history (or all).
- **System prompt**: `/sys [model|all] <text>` — role / answer-language for one model or whole session.
- **Generation settings**: `/opt temperature|top_p|max_tokens|num_ctx|seed <value>` with validation; mapped into Ollama `options` (`max_tokens`→`num_predict`).
- **Honest metrics**: tok/s and token counts taken from Ollama response fields `eval_count`/`eval_duration` (shown as `(ollama)`); own timer only as fallback `(timer)`.
- **[DEMO] label**: every fake offline-generated answer is visibly marked `[DEMO]` in the answer line and demo mode announced at startup.
- Bugfix: duplicated user turns in history when two `/w` raced; crash `Manager.submit(prompt=...)` TypeError.

## v2.0.0-alpha — Global update (cross-platform support)
- **Windows support**: new PowerShell installer `scripts/install.ps1` (winget for Python/Git, official OllamaSetup.exe silent install, `%USERPROFILE%\.servercloud\ServerCloud`, `servercloud.cmd` launcher + PATH).
- **macOS hardening**: Intel/Apple Silicon memory & temperature probing via sysctl/vm_stat/powermetrics; Homebrew path in installer.
- **VPS/cloud support**: `install.sh` now runs headless over SSH as root (no sudo required), added yum/apk package managers, virtualization/VPS auto-detection (`systemd-detect-virt`, DMI product name, hypervisor cpu flag); `/autt` prints Platform + VPS class.
- Cross-platform `/autt`: RAM measurement via ctypes GlobalMemoryStatusEx (Win), sysctl+vm_stat (macOS), psutil fallback everywhere.
- Versioning: alpha suffix support (`2.0.0-alpha`).

## v1.1.1 — Mini update (bugfix, found by real testing)
- Fixed `/w <number>` answering with the model's *name* instead of resolving registry number → now resolves `[NN]` numbers strictly and falls back to exact/unique catalog name; unknown or ambiguous names produce a clear error instead of silently asking a fake model.
- Fixed double brackets in answer line `> [[01] model]` → correct format `> [01] model - answer [time] [tokens]`.
- Live dashboard line now shows `[NN] model` consistently with the answer format.

## v1.1.0 — Major update
- Catalog expanded from 20 to **43 models**, including heavy class (>16 GB SSD): llama3.1:70b, mixtral:8x22b, mistral-large, qwen2.5:32b, deepseek-r1:32b, gemma3:27b and more; tagged `[HEAVY >16GB]` with disk-space check before download.
- **`/autt [model]`** — hardware power measurement (CPU cores, load, RAM, SSD, SoC temp → POWER SCORE 0..100) and automatic tokens/sec recommendation tuned to the device (`/stf` applied on confirm). New module `servercloud/core/hardware.py`.
- **`/dnm [github url]`** — load custom model from GitHub: direct .gguf/Modelfile raw link, blob link (auto→raw), or plain repo URL (README scanned for HF/gguf links). Downloaded via `servercloud/modules/custom_models.py`, registered in Ollama (`ollama create`) when online, numbered [NN] right after.
- **`/dnmf [path]`** — load your own local .gguf / Modelfile from the device into registry + Ollama.
- **`/delm [name/#]`** — delete a downloaded model from registry (and `ollama rm` when possible).
- Heavy-model guard: warning + confirmation if free SSD < needed size.

## v1.0.0 — Initial release
- 20-model catalog, Download Y/n flow, parallel `/w` questions, `/stf` tok/s cap, live dashboard, numbered models [01],[02]..., Termux/Linux support via Ollama.


### 🐛 Fixed (bughunt release-wide)
- `/opt 01 temperature` (documented form) now shows the model's option instead of "Unknown option '01'"; command dispatch rewritten.
- `/stop` no longer leaks the full hidden generation into chat history — only visible text is stored, tagged `[stopped by user]`.
- `pull_model()` false "Download failed" on Ollama builds without final success line fixed (stream completion w/o error = success).
- REPL prefix collisions gone (`/watson …` ≠ `/w …`, `/dlsx` ≠ `/dl sx`) — dispatch on first word.
- Tests no longer write to the real ~/.servercloud/chat.json (temp store).
- TOKENPFS_HOME/TOKENPFS_DATA split: installer checkout dir vs app data dir can no longer collide.
- API model refs accept "01"/"1" interchangeably (leading-zero normalization).

