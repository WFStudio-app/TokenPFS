#!/usr/bin/env python3
"""TokenPFS — local token factory for Ollama models on Termux.

Flow:
  1) pick from a catalog of 20 local models
  2) Download [model]? Y/n -> pull via Ollama, model gets number [01],[02]...
  3) /w [model#] [question]  ask (several questions to different models run
     in parallel)
  4) /stf [tokens/sec]       set generation speed cap
  Live dashboard while generating:
     Text — [model] [doing what] [tok/s] [ready in Ns]
  Final answer line:
     > [model] - [answer] [time] [consumed tokens]
"""

import os
import re
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tokenpfs.core.version import APP_NAME, version_string          # noqa: E402
from tokenpfs.core.models import (MODEL_CATALOG, catalog_lines, get_by_index,
                                  giant_catalog_lines, HEAVY_THRESHOLD_GB)  # noqa: E402

from tokenpfs.core.registry import Registry                          # noqa: E402
from tokenpfs.core.jobs import Manager                               # noqa: E402
from tokenpfs.core.chatml import ChatStore                           # noqa: E402
from tokenpfs.core.options import GenOptions                         # noqa: E402
from tokenpfs.core import hardware                                   # noqa: E402
from tokenpfs.modules import ollama_api                               # noqa: E402
from tokenpfs.modules import custom_models                           # noqa: E402
from tokenpfs.modules.api_server import (ApiKey, KeyStore, ApiServer,
                                         generate_key)                 # noqa: E402
from tokenpfs.utils.colors import banner, c, GREEN, YELLOW, RED, MAGENTA, BOLD  # noqa: E402

# NOTE: TOKENPFS_HOME is used by scripts/install.sh as the *checkout* dir.
# The app's data dir must not collide with it -> use TOKENPFS_DATA instead.
DATA_DIR = os.environ.get("TOKENPFS_DATA",
                          os.path.join(os.path.expanduser("~"), ".tokenpfs"))
os.makedirs(DATA_DIR, exist_ok=True)


class App:
    def __init__(self):
        self.reg = Registry(os.path.join(DATA_DIR, "models.json"))
        self.tps = 8.0
        self.mgr = Manager(self._runner)
        self.chat = ChatStore(os.path.join(DATA_DIR, "chat.json"))
        self.opts = GenOptions()
        self.opt_model = None   # model targeted by /opt
        self.ok = ollama_api.is_alive()
        self.ver = ollama_api.server_version()
        # ---- network API (host your local models over the LAN/WAN) ----
        self.keystore = KeyStore(os.path.join(DATA_DIR, "api_keys.json"))
        self.api = None                 # ApiServer instance when running
        api_host = os.environ.get("TOKENPFS_API_HOST", "0.0.0.0")
        api_port = int(os.environ.get("TOKENPFS_API_PORT", "8777"))
        try:
            self.api = ApiServer(api_host, api_port,
                                 resolver=self._api_resolve,
                                 generator=self._api_generate,
                                 history_provider=lambda num: self.chat.history(num),
                                 keystore=self.keystore,
                                 version=version_string())
            self.api.start()
        except OSError as e:
            print(c(f"API server could not bind {api_host}:{api_port} — {e}", YELLOW))
            self.api = None

    # ---------- network API helpers ----------
    def _api_resolve(self, ref):
        """Map a key-bound model reference to a real Ollama model name.

        Accepts registry numbers ("01"), catalog numbers ("3" / "03") and
        exact model names; returns None if the model is not resolvable.
        """
        num, entry = self.reg.find(ref)
        if entry:
            return entry["name"]
        if str(ref).isdigit() and 1 <= int(ref) <= len(MODEL_CATALOG):
            return MODEL_CATALOG[int(ref) - 1][0]
        matches = [n for n, _, _, _ in MODEL_CATALOG if n == ref]
        return matches[0] if matches else None

    def _api_generate(self, model_name, prompt, options):
        """Blocking generation for API requests (no throttle cap here)."""
        if not self.ok:
            # demo mode mirrors REPL behaviour when Ollama is offline
            return (f"[DEMO MODE — Ollama offline] I am {model_name}. "
                    f"Received {len(prompt)} chars of prompt.")
        text, _n, _el, _stats = ollama_api.generate_stream(
            model_name, prompt, tokens_per_sec=100000.0,
            on_token=None, stop_flag=None, options=options)
        return text

    def _api_url_hint(self):
        if not self.api:
            return "offline"
        host = self.api.host
        if host in ("0.0.0.0", "::"):
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                host = s.getsockname()[0]
                s.close()
            except Exception:
                host = socket.gethostbyname(socket.gethostname())
        return f"http://{host}:{self.api.port}"

    # ---------- /apis /apim /apioff /apion ----------
    def cmd_apis(self, rest):
        """Create a new API key and start serving it.

        Usage: /apis [models] [Y/N history] [req/min] [key slot number]
        Example: /apis 01,02,03 Y 60 1
        """
        parts = rest.split()
        if len(parts) < 4:
            print(c("Usage: /apis [model numbers, e.g. 01,02,03] "
                    "[history access Y/N] [max req/min] [key slot number]", YELLOW))
            print(c("Example: /apis 01,02,03 Y 60 1", YELLOW))
            return
        models_raw, hist_raw, rpm_raw, slot_raw = parts[0], parts[1], parts[2], parts[3]
        # validate models list against registry + catalog
        models = [m.strip() for m in models_raw.split(",") if m.strip()]
        if not models:
            print(c("No model numbers given.", RED))
            return
        bad = []
        for m in models:
            num, entry = self.reg.find(m)
            in_catalog = m.isdigit() and 1 <= int(m) <= len(MODEL_CATALOG)
            if not entry and not in_catalog:
                bad.append(m)
        if bad:
            print(c(f"Unknown model numbers: {', '.join(bad)}. "
                    f"See /list (downloaded) or /models (catalog).", RED))
            return
        # history flag
        h = hist_raw.strip().lower()
        if h in ("y", "yes", "д"):
            allow_hist = True
        elif h in ("n", "no", "н"):
            allow_hist = False
        else:
            print(c("History access must be Y or N.", RED))
            return
        # rate limit
        try:
            rpm = int(rpm_raw)
            if not (1 <= rpm <= 10000):
                raise ValueError
        except ValueError:
            print(c("Requests/min must be an integer 1..10000.", RED))
            return
        # slot number
        if not slot_raw.isdigit() or not (1 <= int(slot_raw) <= 9999):
            print(c("Key slot number must be an integer 1..9999.", RED))
            return
        slot = str(int(slot_raw))
        if self.keystore.get_by_number(slot):
            print(c(f"API key #{slot} already exists. Remove it with "
                    f"/apidel {slot} or pick another number.", RED))
            return
        key = ApiKey(slot, generate_key(), models, allow_hist, rpm)
        self.keystore.add(key)
        print(c(f"API key #{slot} created:", BOLD))
        print(f"   Key        : {c(key.key, GREEN)}")
        print(f"   Models     : {', '.join(models)}")
        print(f"   History    : {'allowed' if allow_hist else 'denied'}")
        print(f"   Rate limit : {rpm} req/min")
        print(f"   Endpoint   : {self._api_url_hint()}")
        if self.api:
            print(c("Server is LIVE now. Client example:", BOLD))
            print(f"   curl -X POST {self._api_url_hint()}/v1/chat \\")
            print(f"     -H 'Authorization: Bearer {key.key}' \\")
            print(f"     -d '{{\"model\":\"{models[0]}\",\"messages\":[{{\"role\":\"user\",\"content\":\"Привет\"}}]}}'")
        else:
            print(c("WARNING: API server is not running (port busy?) — "
                    "the key is saved but cannot be used yet.", YELLOW))

    def cmd_apim(self, rest):
        """/apim — manage/monitor API keys."""
        keys = self.keystore.all()
        state = c("RUNNING", GREEN) if (self.api and self.api.running) else c("STOPPED", RED)
        print(c(f"API server: {state} at {self._api_url_hint()}", BOLD))
        if not keys:
            print(c("No API keys yet. Create one: /apis 01,02 Y 60 1", YELLOW))
            return
        print(c("Keys:", BOLD))
        for n in sorted(keys, key=lambda x: int(x)):
            k = keys[n]
            flag = c("[on ]", GREEN) if k.enabled else c("[OFF]", YELLOW)
            hist = "hist=Y" if k.allow_history else "hist=N"
            print(f"  #{n:>3} {flag} {k.key}  models=[{','.join(k.models)}] "
                  f"{hist} {k.rpm} req/min  served={k.total_requests}  since {k.created}")
        print(c("Commands: /apioff <#> | /apion <#> | /apidel <#>", YELLOW))

    def _set_key_enabled(self, arg, enabled):
        if not arg.isdigit():
            print(c("Usage: /apioff <key number> | /apion <key number>", YELLOW))
            return
        k = self.keystore.get_by_number(arg)
        if not k:
            print(c(f"API key #{arg} not found (see /apim).", RED))
            return
        k.enabled = enabled
        self.keystore.save()
        what = "enabled (/apion)" if enabled else "disabled (/apioff)"
        print(c(f"API key #{arg} {k.key} {what}.", GREEN if enabled else YELLOW))

    def cmd_apioff(self, arg):
        self._set_key_enabled(arg.strip(), False)

    def cmd_apion(self, arg):
        self._set_key_enabled(arg.strip(), True)

    def cmd_apidel(self, arg):
        if not arg.isdigit():
            print(c("Usage: /apidel <key number>", YELLOW))
            return
        k = self.keystore.remove(arg)
        if not k:
            print(c(f"API key #{arg} not found.", RED))
            return
        print(c(f"API key #{arg} ({k.key}) deleted.", GREEN))


    # ---- ollama runner with graceful fallback (demo mode if offline) ----
    def _runner(self, model, prompt, tps, on_token, stop_flag, number=None):
        if not self.ok:
            return self._demo_runner(model, prompt, tps, on_token,
                                     stop_flag, number)
        try:
            return ollama_api.generate_stream(model, prompt, tps,
                                              on_token, stop_flag,
                                              options=self.opts.payload_options(number))
        except Exception as e:
            raise RuntimeError(f"ollama error: {e}")

    @staticmethod
    def _demo_runner(model, prompt, tps, on_token, stop_flag, number=None):
        """Offline demo so the UX is testable without Ollama installed."""
        # show only the last user turn, not the raw ChatML context blob
        last_user = prompt
        if "<|im_start|>" in prompt:
            chunks = [part for part in prompt.split("<|im_start|>")
                      if part.startswith("user")]
            if chunks:
                last_user = chunks[-1].split("<|im_end|>")[0]
                last_user = last_user.split("\n", 1)[-1]
        text = (f"[DEMO MODE — Ollama offline] I am {model}. You asked: "
                f"{last_user!r}. Install & start Ollama (pkg install ollama; "
                f"ollama serve) to get real answers generated locally.")
        start = time.time()
        words = text.split(" ")
        n = 0
        period = 1.0 / max(tps, 0.1)
        for w in words:
            if stop_flag.is_set():
                break
            time.sleep(period)
            on_token(w + " ")
            n += 1
        stats = {"source": "demo", "eval_count": n, "eval_duration_us": 0,
                 "prompt_eval_count": 0, "real_tps": 0.0}
        return text, n, time.time() - start, stats

    # ---- commands ----
    def cmd_models(self):
        n = len(MODEL_CATALOG)
        heavy = sum(1 for _, s, _, _ in MODEL_CATALOG if s >= HEAVY_THRESHOLD_GB)
        print(c(f"Catalog of {n} local models ({heavy} heavy >16 GB; "
                f"use /bmc for 25 GB+ giants):", BOLD))
        for line in catalog_lines():
            print("  " + line)

    def cmd_bmc(self):
        """/bmc — Big Model Catalog: 25 GB+ giants only."""
        lines = giant_catalog_lines()
        print(c(f"BIG MODEL CATALOG (/bmc) — {len(lines)} models needing "
                f">=25 GB free SSD:", BOLD))
        for line in lines:
            print("  " + c(line, MAGENTA))
        print(c("Tip: /dl <catalog number from /models> to download any of them. "
                "Check your disk first with /autt.", YELLOW))

    def confirm_download(self, name):
        ans = input(c(f"Download [{name}]? Y/n ", YELLOW)).strip().lower()
        return ans in ("", "y", "yes", "д")

    def _disk_check(self, size_gb, name):
        """Warn/confirm when model needs more SSD than available."""
        hw = hardware.measure()
        free = hw["disk_free_gb"]
        need = max(size_gb * 1.2, 0.5)   # headroom for unpacking
        if size_gb >= HEAVY_THRESHOLD_GB:
            print(c(f"NOTE: [{name}] is a HEAVY model (>{HEAVY_THRESHOLD_GB:.0f} GB). "
                    f"It targets servers/workstations with big SSDs.", YELLOW))
        if free and free < need:
            print(c(f"WARNING: only {free:.1f} GB free on disk, ~{need:.1f} GB needed.", RED))
            ans = input(c("Download anyway? y/N ", YELLOW)).strip().lower()
            if ans not in ("y", "yes"):
                return False
        return True

    def download(self, idx_or_name):
        name = None
        size = 0.0
        if idx_or_name.isdigit() and 1 <= int(idx_or_name) <= len(MODEL_CATALOG):
            name, size, _, _ = MODEL_CATALOG[int(idx_or_name) - 1]
        else:
            for n, s, _, _ in MODEL_CATALOG:
                if n == idx_or_name:
                    name, size = n, s
        if not name:
            print(c("Unknown model or catalog number.", RED))
            return
        if not self._disk_check(size, name):
            print(c("Cancelled.", YELLOW))
            return
        if not self.confirm_download(name):
            print(c("Cancelled.", YELLOW))
            return
        if self.ok:
            def prog(obj):
                st = obj.get("status", "")
                p = obj.get("completed", 0)
                tot = obj.get("total", 0)
                if tot:
                    pct = 100 * p / tot
                    bar = "#" * int(pct // 4)
                    print(f"\r  downloading {name}: [{bar:<25}] {pct:5.1f}%",
                          end="", flush=True)
                elif st:
                    print(f"\r  {name}: {st}", end="", flush=True)
            ok = ollama_api.pull_model(name, prog)
            print()
            if not ok:
                print(c("Download failed.", RED))
                return
        num = self.reg.add(name, size)
        print(c(f"Model ready: [{num}] {name}", GREEN))

    def _resolve_model(self, key, quiet=False):
        """Resolve model by registry number, exact name, or unique catalog name."""
        num, entry = self.reg.find(key)
        if entry:
            return num, entry["name"]
        # not in registry: try catalog (user may ask a catalog model directly)
        matches = [(n, s) for n, s, _, _ in MODEL_CATALOG if n == key]
        if not matches:
            matches = [(n, s) for n, s, _, _ in MODEL_CATALOG if n.startswith(key)]
        if len(matches) == 1:
            return "?", matches[0][0]
        if len(matches) > 1:
            if not quiet:
                print(c(f"Ambiguous model '{key}': {', '.join(n for n, _ in matches[:5])}...", YELLOW))
            return None, None
        if not quiet:
            print(c(f"Unknown model: {key}. Download it with /dl <number> "
                    f"(see /models) or use its exact name.", RED))
        return None, None

    def ask(self, rest):
        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            print(c("Usage: /w [model number or name] [question]", YELLOW))
            return
        key, question = parts
        num, model_name = self._resolve_model(key)
        if not model_name:
            return
        # chat mode: build prompt with full dialog context (system + history),
        # then register the user turn once (no double insert into history)
        prompt = self.chat.build_prompt(num, question)
        self.chat.add(num, "user", question)
        job = self.mgr.submit(num, model_name, question, self.tps,
                              prompt_full=prompt, chat=self.chat,
                              user_turn_added=True)
        hist = len(self.chat.history(num)) - 1   # exclude just-added user turn
        print(c(f"Job #{job.id} started → [{num}] {model_name} "
                f"@ cap {self.tps:.1f} tok/s (chat history: {hist} msg)", GREEN))

    def cmd_sys(self, rest):
        """/sys [model|all] [text] — system prompt (role / answer language)."""
        parts = rest.split(maxsplit=1)
        if not parts:
            cur_all = self.chat.get_system("all")
            print(c(f"System prompt (session): {cur_all or '(not set)'}", YELLOW))
            return
        if len(parts) == 1:
            target, text = "all", parts[0]
        else:
            key, text = parts
            num, _ = self._resolve_model(key)
            target = num if num and num != "?" else ("all" if key == "all" else None)
            if target is None:
                return
        self.chat.set_system(target, text)
        scope = "whole session" if target == "all" else f"model [{target}]"
        print(c(f"System prompt set for {scope}: {text!r}", GREEN))

    def cmd_opt(self, rest):
        """(/opt|/o) [model] [key value | key | unset key] — gen settings.

        Accepted forms (all documented in the usage line):
          /opt                          -> session summary
          /opt temperature              -> show one option (session)
          /opt 01 temperature           -> show one option (model 01)
          /opt temperature 0.7          -> set (session)
          /opt 01 temperature 0.7       -> set (model 01)
          /opt unset temperature        -> reset session key to default
          /opt 01 unset temperature     -> drop model override
        A bare number ('01', '1') is ALWAYS a model reference; anything
        else that resolves to exactly one model is treated as a model too
        (so '/opt qwen temperature' works), unless it is an option keyword.
        """
        parts = rest.split()
        target = None
        if parts:
            first = parts[0].lower()
            looks_like_model = bool(re.fullmatch(r"\d{1,2}", first)) or \
                               (first not in GenOptions.KEYS and first != "unset")
            if looks_like_model:
                num, name = self._resolve_model(parts[0], quiet=True)
                if name:
                    target = str(num)
                    parts = parts[1:]
                elif re.fullmatch(r"\d{1,2}", first):
                    print(c(f"Unknown model '{parts[0]}'. Download it with "
                            f"/dl <number> (see /models).", RED))
                    return
        if not parts:                     # bare /opt -> show effective summary
            scope = f" for model [{target}]" if target else " (session default)"
            print(c("Generation options" + scope + ": " + self.opts.summary(target), BOLD))
            print(c("Usage: /opt [model] temperature 0.7 | top_p 0.9 | "
                    "max_tokens 512 | num_ctx 2048 | seed -1\n"
                    "       /opt [model] temperature   (show one) | "
                    "/opt [model] unset temperature", YELLOW))
            return
        key = parts[0].lower()
        if key == "unset":
            if len(parts) >= 2:
                ok, msg = self.opts.unset(target, parts[1])
            else:
                ok, msg = (False, "Usage: /opt [model] unset <key>")
            print(c(msg, GREEN if ok else RED))
            return
        if len(parts) == 1:               # show single option
            val = self.opts.get(target, key)
            if val is None:
                scope = f"model [{target}]" if target else "session"
                print(c(f"Option '{key}' is not set for {scope} "
                        f"(Ollama default used).", YELLOW))
            else:
                print(c(f"{key} = {val}" +
                        (f" (model [{target}])" if target else " (session)"), BOLD))
            return
        ok, msg = self.opts.set(target, key, parts[1])
        print(c(msg, GREEN if ok else RED))

    def cmd_clear(self, rest):
        """/clear [model] — reset chat history for one model or all."""
        arg = rest.strip()
        if not arg:
            self.chat.clear()
            print(c("Chat history cleared for ALL models.", GREEN))
            return
        num, _ = self._resolve_model(arg)
        if not num:
            return
        self.chat.clear(num)
        print(c(f"Chat history cleared for model [{num}].", GREEN))

    def dashboard(self):
        active = self.mgr.active()
        if not active:
            print(c("No active jobs.", YELLOW))
            return
        print(c("Live generation:", BOLD))
        for j in active:
            print(f"  Text — {j.status_line()}")

    # ---- /autt : hardware power measurement + auto token tuning ----
    def cmd_autt(self, arg=""):
        hw = hardware.measure()
        temp = f"{hw['temp_c']:.0f} C" if hw["temp_c"] is not None else "n/a"
        print(c("Hardware power measurement:", BOLD))
        plat = f"{hw.get('os', '?')} {hw.get('os_release', '')} ({hw.get('arch', '?')})"
        vps = hw.get("vps")
        if vps:
            plat += f" — virtualized/VPS: {vps}"
        print(f"   Platform       : {plat}")
        print(f"   CPU cores      : {hw['cores']}")
        print(f"   Load (1 min)   : {hw['load1']:.2f}")
        print(f"   RAM free       : {hw['ram_avail_mb']} MB / {hw['ram_total_mb']} MB")
        print(f"   SSD/HDD free   : {hw['disk_free_gb']} GB")
        print(f"   SoC temp       : {temp}")
        score = hw["power_score"]
        grade = ("weak phone" if score < 25 else
                 "phone / SBC" if score < 45 else
                 "laptop" if score < 70 else "server / workstation")
        print(f"   POWER SCORE    : {score}/100  -> class: {grade}")
        # pick model to tune for
        name = size = None
        if arg:
            num, entry = self.reg.find(arg)
            if entry:
                name, size = entry["name"], entry.get("size_gb", 1.0)
            else:
                for n_, s_, _, _ in MODEL_CATALOG:
                    if n_ == arg or str(MODEL_CATALOG.index((n_, s_, _, _)) + 1) == arg:
                        name, size = n_, s_
        if not name:
            items = self.reg.all()
            if items:
                last = sorted(items)[-1]
                name, size = items[last]["name"], items[last].get("size_gb", 1.0)
                print(c(f"No model given — using latest downloaded [{last}] {name}", YELLOW))
            else:
                name, size = "qwen2.5:0.5b", 0.4
                print(c("No models downloaded — showing recommendation for lightest catalog model.", YELLOW))
        tps = hardware.recommend_tps(size, hw)
        heavy_tag = " [HEAVY >16GB]" if size >= HEAVY_THRESHOLD_GB else ""
        print(c(f"Recommended for [{name}] (~{size} GB){heavy_tag}: "
                f"/stf {tps} tokens/sec", GREEN))
        ans = input(c("Apply this speed now? Y/n ", YELLOW)).strip().lower()
        if ans in ("", "y", "yes"):
            self.tps = tps
            print(c(f"Applied: generation speed = {tps} tok/s", GREEN))

    # ---- custom models: /dnm (GitHub), /dnmf (local file), /delm ----
    def cmd_dnm(self, url):
        if not url:
            print(c("Usage: /dnm [github link to .gguf/Modelfile or repo URL]", YELLOW))
            return
        norm = custom_models.normalize_github_url(url)
        m = re.match(r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)/?$", norm)
        if m:  # plain repo -> scan README for links
            owner, repo = m.groups()
            print(c(f"Scanning README of {owner}/{repo} for model files...", YELLOW))
            links = custom_models.scan_repo_readme(owner, repo)
            if not links:
                print(c("No .gguf/.bin/HF links found in README. "
                        "Link the file directly: /dnm <raw-url-to-file>", RED))
                return
            print(c("Found model links:", BOLD))
            for i, ln in enumerate(links, 1):
                print(f"  {i}. {ln}")
            sel = input(c(f"Download which number? (1-{len(links)}) ", YELLOW)).strip()
            if not sel.isdigit() or not (1 <= int(sel) <= len(links)):
                print(c("Cancelled.", YELLOW))
                return
            norm = links[int(sel) - 1]
        name = custom_models.name_from_url(norm)
        if not self.confirm_download(name):
            print(c("Cancelled.", YELLOW))
            return
        try:
            dest_dir = os.path.join(DATA_DIR, "custom")
            path = custom_models.fetch_file_to(norm, dest_dir)
        except Exception as e:
            print(c(f"Fetch failed: {e}", RED))
            return
        size = custom_models.size_gb(path)
        ok_ollama = False
        if path.endswith(".gguf") and self.ok:
            mf = os.path.join(DATA_DIR, "custom", f"Modelfile.{name.replace('/', '_').replace(':', '_')}")
            with open(mf, "w") as f:
                f.write(custom_models.make_modelfile(path))
            ok_ollama = custom_models.register_with_ollama(mf, name)
            print(c("Registered in Ollama." if ok_ollama
                    else "Ollama create failed — registry-only mode.", YELLOW))
        elif not self.ok:
            print(c("Ollama offline — registered in TokenPFS registry only (demo).", YELLOW))
        num = self.reg.add(name, size)
        print(c(f"Custom model ready: [{num}] {name} ({size} GB, source: GitHub)", GREEN))

    def cmd_dnmf(self, path):
        if not path:
            print(c("Usage: /dnmf [path to .gguf or Modelfile on device]", YELLOW))
            return
        path = os.path.expanduser(path.strip())
        if not os.path.exists(path):
            print(c(f"File not found: {path}", RED))
            return
        base = os.path.basename(path)
        name = f"custom/{re.sub(r'\\.gguf$', '', base, flags=re.I).lower()}:latest"
        if not self.confirm_download(name):
            print(c("Cancelled.", YELLOW))
            return
        size = custom_models.size_gb(path)
        if not self._disk_check(0, name):
            return
        ok_ollama = False
        if self.ok:
            if path.endswith(".gguf"):
                mf = os.path.join(DATA_DIR, "custom", f"Modelfile.{name.replace('/', '_').replace(':', '_')}")
                os.makedirs(os.path.dirname(mf), exist_ok=True)
                with open(mf, "w") as f:
                    f.write(custom_models.make_modelfile(path))
                ok_ollama = custom_models.register_with_ollama(mf, name)
            elif base.lower().startswith("modelfile"):
                ok_ollama = custom_models.register_with_ollama(path, name)
            print(c("Registered in Ollama." if ok_ollama
                    else "Ollama create failed — registry-only mode.", YELLOW))
        else:
            print(c("Ollama offline — registered in TokenPFS registry only (demo).", YELLOW))
        num = self.reg.add(name, size)
        print(c(f"Local model ready: [{num}] {name} ({size} GB, source: local file)", GREEN))

    def cmd_delm(self, key):
        if not key:
            print(c("Usage: /delm [model name or number]", YELLOW))
            return
        num, entry = self.reg.remove(key)
        if not num:
            print(c(f"Model not found: {key}", RED))
            return
        # try removing from ollama too
        removed_ollama = ""
        if self.ok:
            import subprocess
            try:
                r = subprocess.run(["ollama", "rm", entry["name"]],
                                   capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    removed_ollama = " (+ deleted from Ollama storage)"
            except Exception:
                pass
        print(c(f"Deleted [{num}] {entry['name']}{removed_ollama}", GREEN))

    def status_loop(self, stop_event):
        last_print = 0.0
        while not stop_event.is_set():
            now = time.time()
            lines = self.mgr.result_lines()
            for ln in lines:
                sys.stdout.write("\n" + c(ln, MAGENTA) + "\n")
                sys.stdout.flush()
            if now - last_print >= 1.0 and self.mgr.active():
                last_print = now
                for j in self.mgr.active():
                    sys.stdout.write(f"\r  ⚙ {j.status_line()}   ")
                    sys.stdout.flush()
            time.sleep(0.2)
        print()

    # ---- main REPL ----
    def run(self):
        api_line = (f"API {self._api_url_hint()}" if (self.api and self.api.running)
                    else "API offline")
        print(banner(version_string(), self.ok, self.ver, len(self.reg.all()),
                     extra=[f"    /apis /apim /apioff /apion   network API keys | {api_line}"]))
        if not self.ok:
            print(c("Ollama not reachable — running in DEMO mode "
                    "(fake generation).", YELLOW))
        stop_event = threading.Event()
        dash = threading.Thread(target=self.status_loop, args=(stop_event,),
                                daemon=False)
        dash.start()
        print(c("Type 'help' for commands.", YELLOW))
        while True:
            try:
                line = input(c("tokenpfs> ", GREEN)).strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            low = line.lower()
            # dispatch on the FIRST whitespace-delimited word only, so that
            # '/watson test' is never mistaken for '/w atson test', and
            # '/dlsx' is reported as an unknown command instead of running /dl.
            head = low.split(maxsplit=1)[0]
            arg = line[len(head):].strip()
            if head in ("quit", "exit"):
                break
            elif head == "help":
                print("/models | /bmc (25GB+ giants) | /dl <n> | /list | "
                      "/w <model> <text> (chat) | "
                      "/sys [model|all] <prompt> | /opt [model] <key> [val] | "
                      "/clear [model] | /stf <tps> | /autt [model] | "
                      "/dnm <github-url> | /dnmf <path> | /delm <name/#> | "
                      "/apis <01,02> <Y/N hist> <req/min> <slot#> | "
                      "/apim | /apioff <#> | /apion <#> | /apidel <#> | "
                      "/status | /stop <job id> | quit")
            elif head == "/models":
                self.cmd_models()
            elif head == "/bmc":
                self.cmd_bmc()
            elif head == "/dnmf":
                self.cmd_dnmf(arg)
            elif head == "/dnm":
                self.cmd_dnm(arg)
            elif head == "/delm":
                self.cmd_delm(arg)
            elif head == "/autt":
                self.cmd_autt(arg)
            elif head == "/dl":
                if arg:
                    self.download(arg)
                else:
                    print(c("Usage: /dl <catalog number>", YELLOW))
            elif head == "/list":
                items = self.reg.all()
                if not items:
                    print(c("Nothing downloaded yet. Use /dl <number>.", YELLOW))
                for n, e in items.items():
                    print(f"  [{n}] {e['name']} (~{e['size_gb']} GB)")
            elif head == "/w":
                self.ask(arg)
            elif head == "/sys":
                self.cmd_sys(arg)
            elif head == "/opt":
                self.cmd_opt(arg)
            elif head == "/clear":
                self.cmd_clear(arg)
            elif head == "/stf":
                try:
                    v = float(arg)
                    if not (0.1 <= v <= 1000):
                        raise ValueError
                    self.tps = v
                    print(c(f"Generation speed set to {v:.1f} tokens/sec", GREEN))
                except ValueError:
                    print(c("Usage: /stf <tokens per second> (0.1..1000)", YELLOW))
            elif head == "/status":
                self.dashboard()
            elif head == "/apis":
                self.cmd_apis(arg)
            elif head == "/apim":
                self.cmd_apim(arg)
            elif head == "/apioff":
                self.cmd_apioff(arg)
            elif head == "/apion":
                self.cmd_apion(arg)
            elif head == "/apidel":
                self.cmd_apidel(arg)
            elif head == "/stop":
                found = False
                for j in self.mgr.jobs:
                    if str(j.id) == arg and j.state == "generating":
                        j.stop_flag.set()
                        found = True
                print(c("Job stopped." if found else "Job not found/active.",
                        YELLOW if found else RED))
            else:
                print(c("Unknown command. Type help.", RED))
        # let running generations finish (max 60s), printing their results
        deadline = time.time() + 60
        while self.mgr.active() and time.time() < deadline:
            time.sleep(0.2)
        time.sleep(0.3)  # final flush of result lines
        stop_event.set()
        dash.join(timeout=2)
        if self.api:
            self.api.stop()
        print("Bye.")


def main():
    App().run()


if __name__ == "__main__":
    main()
