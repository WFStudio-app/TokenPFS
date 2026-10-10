"""Catalog of 135 local models available through Ollama.

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
    # ---- heavier models (>16 GB SSD class) ----
    ("llama3.1:70b",       40.0, "Llama",     "Heavyweight, server GPU/NPU"),
    ("qwen2.5:32b",        18.5, "Qwen",      "Strong mid-heavy reasoning"),
    ("mistral-large",      40.5, "Mistral",   "Flagship dense model"),
    ("deepseek-r1:32b",    18.0, "DeepSeek",  "Long-chain reasoning, heavy"),
    ("gemma3:27b",         16.5, "Gemma",     "Google large multimodal"),
    ("qwen2.5-coder:32b",  18.6, "Qwen",      "Coding specialist, heavy"),
    ("codellama:34b",      18.6, "CodeLlama", "Classic heavy coder"),
    ("yi:34b",             19.0, "Yi",        "01.AI large bilingual"),
    ("mixtral:8x22b",      46.0, "Mixtral",   "MoE giant, server class"),
    ("llama2:70b",         34.0, "Llama2",    "Legacy 70B"),
    ("dbrx:instruct",      24.0, "DBRX",      "MoE instruct"),
    ("command-r:35b",      19.7, "Cohere",    "RAG / tool-use heavy"),
    ("qwq:32b",            18.0, "QwQ",       "Research reasoning, heavy"),
    ("glm-4:9b-chat",       5.5, "GLM",       "Zhipu mid-size chat"),
    ("internlm2:20b",      11.0, "InternLM",  "Mid-heavy Chinese/EN"),
    ("nous-hermes2:34b",   19.2, "Hermes",    "Uncensored-style heavy"),
    ("wizardlm2:8x22b",    46.0, "WizardLM",  "MoE creative writing"),
    ("phind-codellama:34b", 19.0, "Phind",     "Search-augmented coder"),
    ("openchat:8b",         4.5, "OpenChat",   "Light chat"),
    ("solar:10.7b",         6.8, "Solar",      "Upcycled mid-size"),
    ("magistral:24b",      14.6, "Magistral",  "Reasoning MoE mid-heavy"),
    ("devstral:24b",       14.6, "Devstral",   "Agentic coding mid-heavy"),
    # ---- new light/mid additions (v2.1) ----
    ("qwen3:0.6b",          0.5, "Qwen3",      "Newest tiny reasoning"),
    ("qwen3:4b",            2.5, "Qwen3",      "Hybrid thinking small"),
    ("qwen3:8b",            5.2, "Qwen3",      "Hybrid thinking 8B"),
    ("gemma3n:e2b",         2.8, "Gemma3n",    "MatFormer edge model"),
    ("granite4:micro",      3.0, "Granite",    "IBM compact function-calling"),
    ("minimax-m2:cloudless",7.9, "MiniMax",    "MoE coding, fits 8GB RAM"),
    ("ernie4.5:0.3b",       0.4, "ERNIE",      "Baidu ultra-tiny multilingual"),
    ("lfm2:1.2b",           0.7, "LFM2",       "Liquid AI, phone-friendly"),
    ("nemotron-mini:4b",    2.6, "Nemotron",   "NVIDIA safety-tuned small"),
    ("exaone4:7.8b",        4.9, "Exaone",     "LG recent multilingual"),
    # ---- giant class (>=25 GB SSD) ----
    ("llama3.3:70b",       40.0, "Llama3.3",   "Best-70B chat, server GPU"),
    ("qwen2.5:72b",        39.0, "Qwen",       "Flagship dense Qwen"),
    ("qwen3:235b-a22b",   128.0, "Qwen3 MoE",  "Frontier MoE, multi-GPU rig"),
    ("deepseek-r1:70b",    40.0, "DeepSeek",   "Long CoT reasoning giant"),
    ("deepseek-v3:671b",  365.0, "DeepSeek",   "Full-size frontier MoE"),
    ("llama4:scout:17b",   25.0, "Llama4",     "Vision MoE entry"),
    ("gpt-oss:120b",       61.0, "OpenAI OSS", "Open-weight reasoning giant"),
    ("mistral-small:24b",  14.5, "Mistral",    "Compact tool-use"),
    ("phi4-reasoning:14b", 9.1, "Phi4",        "Microsoft reasoning mid"),
    ("command-r-plus",     61.0, "Cohere",     "RAG enterprise giant"),
    ("glm-4:32b",          18.0, "GLM",        "Zhipu agentic heavy"),
    ("yi-coder:9b",         5.2, "Yi",         "Light coding specialist"),
    ("codegeex4:9b",        5.5, "CodeGeeX",   "Multilingual coder"),
    ("internlm3:8b",        4.7, "InternLM",   "Recent mid coder"),
    ("aquila2:70b",        34.0, "Aquila2",    "BAAI legacy giant"),
    ("falcon3:10b",         6.5, "Falcon3",    "TII mid-size"),
    ("aya-expanse:32b",    18.5, "Aya",        "Cohere multilingual giant"),
    ("kimi-k2:1t",        594.0, "Kimi",       "Trillion-param MoE, datacenter"),
    ("llama3.1:405b",     231.0, "Llama3.1",   "Dense 405B, cluster class"),
    # ---- Mistral family (full sweep) ----
    ("mistral:7b-instruct-v0.2", 4.1, "Mistral", "v0.2 instruct classic"),
    ("mistral:7b-instruct-v0.3", 4.1, "Mistral", "v0.3 instruct, function-calling"),
    ("mistral-nemo",             7.1, "Mistral", "12B, NVIDIA co-tuned"),
    ("mistral-small3.2:24b",     14.5, "Mistral","Recent small, tool-use"),
    ("mistral-large:2",          40.5, "Mistral","Flagship dense v2"),
    ("minimax-m2:62b",           20.0, "MiniMax","MoE coder on DeepSeek-architecture line"),
    ("pixtral:12b",              7.0, "Pixtral", "Mistral vision 12B"),
    ("magistral:7b",             4.5, "Magistral","Light reasoning MoE"),
    ("devstral-small:24b",       14.6, "Devstral","Agentic coding, Mistral-based"),
    # ---- DeepSeek family (full sweep) ----
    ("deepseek-llm:7b",          4.0, "DeepSeek","Base LLM (no chat tune)"),
    ("deepseek-coder:1.3b",      0.8, "DeepSeek","Tiny coding specialist"),
    ("deepseek-coder:6.7b",      3.8, "DeepSeek","Classic light coder"),
    ("deepseek-coder:33b",       18.6, "DeepSeek","Heavy coder"),
    ("deepseek-coder-v2:16b",    8.9, "DeepSeek","MoE coder v2"),
    ("deepseek-r1:8b",           5.0, "DeepSeek","Reasoning CoT 8B"),
    ("deepseek-r1:14b",          8.7, "DeepSeek","Reasoning CoT 14B"),
    ("deepseek-r1:distill-qwen-1.5b", 1.1, "DeepSeek","R1 distilled into Qwen tiny"),
    ("deepseek-v2:16b",          8.4, "DeepSeek","MLA arch mid-size"),
    ("deepseek-r1:671b",        365.0, "DeepSeek","Full R1 frontier MoE"),
    # ---- Qwen family (full sweep) ----
    ("qwen:7b",                  4.4, "Qwen",     "Original Qwen 1.0 classic"),
    ("qwen:14b",                10.1, "Qwen",     "Original Qwen 1.0 mid"),
    ("qwen:32b",                20.0, "Qwen",     "Original Qwen 1.0 heavy"),
    ("qwen:72b",                 41.0, "Qwen",    "Original Qwen 1.0 flagship"),
    ("qwen2:0.5b",               0.4, "Qwen2",    "Gen-2 tiny"),
    ("qwen2:1.5b",               1.0, "Qwen2",    "Gen-2 light"),
    ("qwen2:7b",                 4.4, "Qwen2",    "Gen-2 solid 7B"),
    ("qwen2:72b",               39.0, "Qwen2",    "Gen-2 dense giant"),
    ("qwen2.5:1.5b",             1.0, "Qwen",     "Small multilingual chat"),
    ("qwen2.5:14b",              8.9, "Qwen",     "Balanced mid-size"),
    ("qwen2.5-coder:1.5b",       1.2, "Qwen",     "Tiny coder"),
    ("qwen2.5-coder:7b",         4.7, "Qwen",     "Light coding specialist"),
    ("qwen2.5-coder:14b",        8.9, "Qwen",     "Mid coder"),
    ("qwen2.5-coder:next:80b",  33.0, "Qwen",     "Next-gen hybrid coder, server class"),
    ("qwen2.5-vl:3b",            3.4, "Qwen-VL",  "Vision-language small"),
    ("qwen2.5-vl:7b",            5.9, "Qwen-VL",  "Vision-language 7B"),
    ("qwen2.5-vl:32b",          21.2, "Qwen-VL",  "Vision-language heavy"),
    ("qwen2.5-vl:72b",          38.0, "Qwen-VL",  "Vision-language giant"),
    ("qwen2.5-math:1.5b",        1.1, "Qwen-Math","Math-tuned tiny"),
    ("qwen2.5-math:7b",          4.5, "Qwen-Math","Math-tuned 7B"),
    ("qwen2.5-math:72b",        39.0, "Qwen-Math","Math-tuned flagship"),
    ("qwq:32b-preview",         19.8, "QwQ",      "Preview reasoning build"),
    ("qwen3:1.7b",               1.4, "Qwen3",    "Tiny reasoning hybrid"),
    ("qwen3:14b",                9.3, "Qwen3",    "Hybrid thinking 14B"),
    ("qwen3:30b-a3b",           18.6, "Qwen3 MoE","MoE 30B / 3B active"),
    ("qwen3:32b",               19.8, "Qwen3",    "Dense flagship 32B"),
    ("qwen3-coder:30b-a3b",     18.6, "Qwen3 MoE","Agentic coding MoE"),
    ("qwen3-coder:480b-a35b",  270.0, "Qwen3 MoE","Frontier coder, cluster class"),
    ("qwen3-vl:8b",              6.0, "Qwen-VL",  "Newest vision-language 8B"),
    ("qwen3-max:cloudless",     12.0, "Qwen3",    "Max-line distilled local"),
    # --- GLM family (Zhipu / Z.ai) ---
    ("glm4v:9b",                 5.5, "GLM-Vision","Vision-language 9B"),
    ("glm-4:9b-0414",            5.5, "GLM",      "GLM-4 9B Apr refresh"),
    ("glm-4-alltools:32b",      19.5, "GLM",      "Agentic tool-use 32B"),
    ("glm-4-0416:32b",          19.5, "GLM",      "GLM-4 flagship refresh"),
    ("chatglm3:6b",              5.0, "ChatGLM",  "Classic bilingual chat 6B"),
    ("chatglm:6b-v2",            6.2, "ChatGLM",  "Gen2 base+chat 32K ctx"),
    ("glm-4.7:cloudless",       14.0, "GLM",      "Latest-gen distilled local"),
    # --- Gemini family (Google, open-weight line) ---
    ("gemma3n:e4b",              3.1, "Gemma",    "Small multimodal 4B-class"),
    ("gemma2:9b",                5.4, "Gemma",    "Gen2 workhorse 9B"),
    ("gemma2:27b",              16.2, "Gemma",    "Gen2 flagship 27B"),
    ("gemma3:12b",               8.1, "Gemma",    "Gen3 vision-language 12B"),
    ("shieldgemma:2b",           1.6, "Gemma",    "Safety/content-moderation"),
    ("embedgemma:300m",          0.3, "Gemma",    "Tiny embeddings model"),
    ("gemini-2.0-flash:cloudless", 10.0, "Gemini", "Flash-line distilled local"),
    ("gemini-2.5-pro:cloudless",   18.0, "Gemini", "Pro-line distilled local"),
]

HEAVY_THRESHOLD_GB = 16.0   # models above this need >16 GB free SSD
GIANT_THRESHOLD_GB = 25.0   # /bmc catalog: 25 GB+ giants


def catalog_lines() -> list:
    out = []
    for i, (name, size, fam, note) in enumerate(MODEL_CATALOG, 1):
        tag = " [HEAVY >16GB]" if size >= HEAVY_THRESHOLD_GB else ""
        out.append(f"{i:>2}. {name:<24} ~{size:>4.1f} GB  [{fam}]{tag}  {note}")
    return out


def get_by_index(idx: int):
    """1-based index into the catalog."""
    if 1 <= idx <= len(MODEL_CATALOG):
        return MODEL_CATALOG[idx - 1][0]
    return None


def giant_catalog_lines() -> list:
    """/bmc — Big Model Catalog: only models that need >=25 GB free SSD."""
    out = []
    giants = [(n, s, f, note) for (n, s, f, note) in MODEL_CATALOG
              if s >= GIANT_THRESHOLD_GB]
    giants.sort(key=lambda m: m[1])  # lightest giant first
    for i, (name, size, fam, note) in enumerate(giants, 1):
        cls = "datacenter" if size >= 200 else ("multi-GPU server" if size >= 60 else "single server GPU")
        out.append(f"{i:>2}. {name:<24} ~{size:>5.1f} GB  [{fam}]  {note}  ({cls})")
    return out
