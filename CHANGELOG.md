### [2.1.1-alpha] — 2026-10-10 (Unreleased)

### Added
- **Catalog expanded 42 → 71 models**: new light/mid class (qwen3:0.6b/4b/8b, gemma3n:e2b, granite4:micro, minimax-m2:cloudless, ernie4.5:0.3b, lfm2:1.2b, nemotron-mini:4b, exaone4:7.8b) and giant class (llama3.3:70b, qwen2.5:72b, deepseek-r1:70b, gpt-oss:120b, command-r-plus, llama3.1:405b, deepseek-v3:671b, kimi-k2:1t…).
- **`/bmc` — Big Model Catalog**: only models needing ≥25 GB free SSD, sorted by size with hardware-class tags (single server GPU / multi-GPU server / datacenter). Magenta output, tip to check disk via `/autt`.
- `/models` header now advertises `/bmc`; `help` lists `/bmc`; banner shows the new command.

 Changelog — TokenPFS

Version algorithm (X.X.X): **X.0.0** global · **0.X.0** major · **0.0.X** mini

## Unreleased — chat & generation upgrade (will be the next release)
- **Chat context**: `/w` is now a real conversation — system prompt + full per-model history (ChatML) sent to Ollama; assistant turns stored automatically. `/clear [model]` resets history (or all).
- **System prompt**: `/sys [model|all] <text>` — role / answer-language for one model or whole session.
- **Generation settings**: `/opt temperature|top_p|max_tokens|num_ctx|seed <value>` with validation; mapped into Ollama `options` (`max_tokens`→`num_predict`).
- **Honest metrics**: tok/s and token counts taken from Ollama response fields `eval_count`/`eval_duration` (shown as `(ollama)`); own timer only as fallback `(timer)`.
- **[DEMO] label**: every fake offline-generated answer is visibly marked `[DEMO]` in the answer line and demo mode announced at startup.
- Bugfix: duplicated user turns in history when two `/w` raced; crash `Manager.submit(prompt=...)` TypeError.

## v2.0.0-alpha — Global update (cross-platform support)
- **Windows support**: new PowerShell installer `scripts/install.ps1` (winget for Python/Git, official OllamaSetup.exe silent install, `%USERPROFILE%\.tokenpfs\TokenPFS`, `tokenpfs.cmd` launcher + PATH).
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
- **`/autt [model]`** — hardware power measurement (CPU cores, load, RAM, SSD, SoC temp → POWER SCORE 0..100) and automatic tokens/sec recommendation tuned to the device (`/stf` applied on confirm). New module `tokenpfs/core/hardware.py`.
- **`/dnm [github url]`** — load custom model from GitHub: direct .gguf/Modelfile raw link, blob link (auto→raw), or plain repo URL (README scanned for HF/gguf links). Downloaded via `tokenpfs/modules/custom_models.py`, registered in Ollama (`ollama create`) when online, numbered [NN] right after.
- **`/dnmf [path]`** — load your own local .gguf / Modelfile from the device into registry + Ollama.
- **`/delm [name/#]`** — delete a downloaded model from registry (and `ollama rm` when possible).
- Heavy-model guard: warning + confirmation if free SSD < needed size.

## v1.0.0 — Initial release
- 20-model catalog, Download Y/n flow, parallel `/w` questions, `/stf` tok/s cap, live dashboard, numbered models [01],[02]..., Termux/Linux support via Ollama.
