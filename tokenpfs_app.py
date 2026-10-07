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
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tokenpfs.core.version import APP_NAME, version_string          # noqa: E402
from tokenpfs.core.models import MODEL_CATALOG, catalog_lines, get_by_index  # noqa: E402
from tokenpfs.core.registry import Registry                          # noqa: E402
from tokenpfs.core.jobs import Manager                               # noqa: E402
from tokenpfs.modules import ollama_api                              # noqa: E402
from tokenpfs.utils.colors import banner, c, GREEN, YELLOW, RED, MAGENTA, BOLD  # noqa: E402

DATA_DIR = os.environ.get("TOKENPFS_HOME",
                          os.path.join(os.path.expanduser("~"), ".tokenpfs"))
os.makedirs(DATA_DIR, exist_ok=True)


class App:
    def __init__(self):
        self.reg = Registry(os.path.join(DATA_DIR, "models.json"))
        self.tps = 8.0
        self.mgr = Manager(self._runner)
        self.ok = ollama_api.is_alive()
        self.ver = ollama_api.server_version()

    # ---- ollama runner with graceful fallback (demo mode if offline) ----
    def _runner(self, model, prompt, tps, on_token, stop_flag):
        if not self.ok:
            return self._demo_runner(model, prompt, tps, on_token, stop_flag)
        try:
            return ollama_api.generate_stream(model, prompt, tps,
                                              on_token, stop_flag)
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
        return text, n, time.time() - start

    # ---- commands ----
    def cmd_models(self):
        print(c("Catalog of 20 local models:", BOLD))
        for line in catalog_lines():
            print("  " + line)

    def confirm_download(self, name):
        ans = input(c(f"Download [{name}]? Y/n ", YELLOW)).strip().lower()
        return ans in ("", "y", "yes", "д")

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

    def ask(self, rest):
        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            print(c("Usage: /w [model number or name] [question]", YELLOW))
            return
        key, question = parts
        num, entry = self.reg.find(key)
        if not entry:
            # allow asking by catalog name even if not downloaded (demo/offline)
            entry = {"name": key}
            num = "?"
        job = self.mgr.submit(num, entry["name"], question, self.tps)
        print(c(f"Job #{job.id} started → [{num}] {entry['name']} "
                f"@ {self.tps:.1f} tok/s", GREEN))

    def dashboard(self):
        active = self.mgr.active()
        if not active:
            print(c("No active jobs.", YELLOW))
            return
        print(c("Live generation:", BOLD))
        for j in active:
            print(f"  Text — {j.status_line()}")

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
                print("/models | /dl <n> | /list | /w <model> <text> | "
                      "/stf <tps> | /status | /stop <job id> | quit")
            elif low == "/models":
                self.cmd_models()
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
