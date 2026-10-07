"""Catalog of 20 local models available through Ollama.

Each model gets a sequential number [01], [02], ... assigned right after
it is downloaded on the device (not from this catalog).
"""

# (name, size_gb_approx, family, note)
MODEL_CATALOG = [
    ("llama3.2:1b",        1.3, "Llama",      "Ultra-light, best for phones"),
    ("qwen2.5:0.5b",       0.4, "Qwen",       "Tiny, fastest on Termux"),
    ("phi3.5:3.8b",        2.2, "Phi",        "Strong reasoning for its size"),
    ("gemma2:2b",          1.6, "Gemma",      "Google small model"),
    ("tinyllama:1.1b",     0.6, "TinyLlama",  "Minimal chat model"),
    ("mistral:7b",         4.1, "Mistral",    "Classic workhorse"),
    ("llama3.1:8b",        4.7, "Llama",      "General purpose"),
    ("qwen2.5:3b",         1.9, "Qwen",       "Good multilingual"),
    ("deepseek-r1:1.5b",   1.1, "DeepSeek",   "Reasoning (CoT), tiny"),
    ("deepseek-r1:7b",     4.7, "DeepSeek",   "Reasoning (CoT)"),
    ("phi3:mini",          2.2, "Phi",        "Microsoft mini"),
    ("gemma3:4b",          3.1, "Gemma",      "Newer Gemma"),
    ("llama3.2:3b",        2.0, "Llama",      "Balanced small Llama"),
    ("qwen2.5:7b",         4.4, "Qwen",       "Strong 7B"),
    ("starling-lm:7b",     4.2, "Starling",   "Helpful assistant"),
    ("neural-chat:7b",     4.0, "Intel",      "Chat fine-tune"),
    ("orca-mini:3b",       1.9, "Orca",       "Instruction tuned"),
    ("smollm2:1.7b",       1.1, "SmolLM",     "HuggingFace small"),
    ("exaone3.5:2.4b",     1.5, "Exaone",     "Multilingual Asian"),
    ("granite3.1-dense:2b", 1.6, "Granite",   "IBM enterprise small"),
]


def catalog_lines() -> list:
    out = []
    for i, (name, size, fam, note) in enumerate(MODEL_CATALOG, 1):
        out.append(f"{i:>2}. {name:<24} ~{size:>4.1f} GB  [{fam}]  {note}")
    return out


def get_by_index(idx: int):
    """1-based index into the catalog."""
    if 1 <= idx <= len(MODEL_CATALOG):
        return MODEL_CATALOG[idx - 1][0]
    return None
