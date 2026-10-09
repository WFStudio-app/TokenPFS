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
                                  HEAVY_THRESHOLD_GB)                # noqa: E402
from tokenpfs.core.registry import Registry                          # noqa: E402
from tokenpfs.core.jobs import Manager                               # noqa: E402
from tokenpfs.core.chatml import ChatStore                           # noqa: E402
from tokenpfs.core.options import GenOptions                         # noqa: E402
from tokenpfs.core import hardware                                   # noqa: E402
from tokenpfs.modules import ollama_api                               # noqa: E402
from tokenpfs.modules import custom_models                           # noqa: E402
from tokenpfs.utils.colors import banner, c, GREEN, YELLOW, RED, MAGENTA, BOLD  # noqa: E402

DATA_DIR = os.environ.get("TOKENPFS_HOME",
                          os.path.join(os.path.expanduser("~"), ".tokenpfs"))
os.makedirs(DATA_DIR, exist_ok=True)


class App:
    def __init__(self):
        self.reg = Registry(os.path.join(DATA_DIR, "models.json"))
        self.tps = 8.0
        self.mgr = Manager(self._runner)
        self.chat = ChatStore(os.path.join(DATA_DIR, "chat.json"))
        self.opts = GenOptions()
        self.ok = ollama_api.is_alive()
        self.ver = ollama_api.server_version()

    # ---- ollama runner with graceful fallback (demo mode if offline) ----
    def _runner(self, model, prompt, tps, on_token, stop_flag):
        if not self.ok:
            return self._demo_runner(model, prompt, tps, on_token, stop_flag)
        try:
            return ollama_api.generate_stream(model, prompt, tps,
                                              on_token, stop_flag,
                                              options=self.opts.payload_options())
        except Exception as e:
            raise RuntimeError(f"ollama error: {e}")

    @staticmethod
    def _demo_runner(model, prompt, tps, on_token, stop_flag):
        """Offline demo so the UX is testable without Ollama installed."""
        text = (f"[DEMO MODE — Ollama offline] I am {model}. You asked: "
                f"{prompt!r}. Install & start Ollama (pkg install ollama; "
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
        print(c(f"Catalog of {n} local models ({heavy} heavy >16 GB):", BOLD))
        for line in catalog_lines():
            print("  " + line)

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

    def _resolve_model(self, key):
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
            print(c(f"Ambiguous model '{key}': {', '.join(n for n, _ in matches[:5])}...", YELLOW))
            return None, None
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
        # chat mode: build prompt with full dialog context (system + history)
        prompt = self.chat.build_prompt(num, question)
        job = self.mgr.submit(num, model_name, question, self.tps,
                              prompt_full=prompt, chat=self.chat)
        hist = len(self.chat.history(num)) - 1   # user turn added by submit()
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
        """/opt [key value] — generation settings (temperature, top_p...)."""
        parts = rest.split(maxsplit=1)
        if not parts:
            print(c("Generation options: " + self.opts.summary(), BOLD))
            print(c("Usage: /opt temperature 0.7 | top_p 0.9 | max_tokens 512 "
                    "| num_ctx 2048 | seed -1", YELLOW))
            return
        key, val = (parts + [""])[:2] if len(parts) == 2 else (parts[0], "")
        if not val:
            print(c("Usage: /opt <key> <value>", YELLOW))
            return
        ok, msg = self.opts.set(key, val)
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
        print(banner(version_string(), self.ok, self.ver, len(self.reg.all())))
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
            if low in ("quit", "exit"):
                break
            elif low == "help":
                print("/models | /dl <n> | /list | /w <model> <text> (chat) | "
                      "/sys [model|all] <prompt> | /opt <key> <val> | "
                      "/clear [model] | /stf <tps> | /autt [model] | "
                      "/dnm <github-url> | /dnmf <path> | /delm <name/#> | "
                      "/status | /stop <job id> | quit")
            elif low == "/models":
                self.cmd_models()
            elif low.startswith("/dnmf"):
                self.cmd_dnmf(line[5:].strip())
            elif low.startswith("/dnm"):
                self.cmd_dnm(line[4:].strip())
            elif low.startswith("/delm"):
                self.cmd_delm(line[5:].strip())
            elif low.startswith("/autt"):
                self.cmd_autt(line[5:].strip())
            elif low.startswith("/dl"):
                arg = line[3:].strip()
                if arg:
                    self.download(arg)
                else:
                    print(c("Usage: /dl <catalog number>", YELLOW))
            elif low == "/list":
                items = self.reg.all()
                if not items:
                    print(c("Nothing downloaded yet. Use /dl <number>.", YELLOW))
                for n, e in items.items():
                    print(f"  [{n}] {e['name']} (~{e['size_gb']} GB)")
            elif low.startswith("/w"):
                self.ask(line[2:].strip())
            elif low.startswith("/sys"):
                self.cmd_sys(line[4:].strip())
            elif low.startswith("/opt"):
                self.cmd_opt(line[4:].strip())
            elif low.startswith("/clear"):
                self.cmd_clear(line[6:].strip())
            elif low.startswith("/stf"):
                arg = line[4:].strip()
                try:
                    v = float(arg)
                    if not (0.1 <= v <= 1000):
                        raise ValueError
                    self.tps = v
                    print(c(f"Generation speed set to {v:.1f} tokens/sec", GREEN))
                except ValueError:
                    print(c("Usage: /stf <tokens per second> (0.1..1000)", YELLOW))
            elif low == "/status":
                self.dashboard()
            elif low.startswith("/stop"):
                arg = line[5:].strip()
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
        print("Bye.")


def main():
    App().run()


if __name__ == "__main__":
    main()
