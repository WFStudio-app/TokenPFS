# Changelog — TokenPFS

Version algorithm (X.X.X): **X.0.0** global · **0.X.0** major · **0.0.X** mini

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
