"""Parallel generation manager.

Each question runs in its own worker thread against Ollama, so several
models can generate answers simultaneously. A live status line per job:

  Text — [model name] [what it's doing now] [tokens/sec] [ETA]
"""

import threading
import time


class Job:
    _seq = itertools_count = None

    def __init__(self, jid, number, model, prompt, tps, runner):
        self.id = jid
        self.number = number      # "07"
        self.model = model
        self.prompt = prompt
        self.tps = tps            # tokens per second target
        self.runner = runner      # callable(model, prompt, tps, on_token, stop_flag)
        self.state = "queued"     # queued | generating | done | error | stopped
        self.tokens_out = 0
        self.started = None
        self.finished = None
        self.answer = ""
        self.error = None
        self.stop_flag = threading.Event()
        self.lock = threading.Lock()

    def rate(self):
        if not self.started or self.state not in ("generating",):
            return 0.0
        dt = time.time() - self.started
        return self.tokens_out / dt if dt > 0 else 0.0

    def eta(self, est_total=512):
        r = self.rate()
        if r <= 0:
            return None
        return max(0.0, (est_total - self.tokens_out) / r)

    def status_line(self):
        act = {"queued": "waiting", "generating": f"generating ({self.tokens_out} tok)",
               "done": "finished", "error": "failed", "stopped": "stopped"}[self.state]
        eta = self.eta()
        eta_s = f"{eta:.0f}s" if eta is not None else "?"
        label = f"[{self.number}] {self.model}" if self.number not in ("?", "") else self.model
        return (f"{label} [{act}] [{self.rate():.1f} tok/s] [ready in {eta_s}]")


class Manager:
    def __init__(self, runner):
        self.runner = runner
        self.jobs = []
        self._lock = threading.Lock()
        self._next_id = 1

    def submit(self, number, model, prompt, tps) -> Job:
        with self._lock:
            jid = self._next_id
            self._next_id += 1
        job = Job(jid, number, model, prompt, tps, self.runner)
        with self._lock:
            self.jobs.append(job)
        t = threading.Thread(target=self._run, args=(job,), daemon=True)
        t.start()
        return job

    def _run(self, job: Job):
        job.state = "generating"
        job.started = time.time()

        def on_token(tok):
            with job.lock:
                job.answer += tok
                job.tokens_out += 1

        try:
            text, ntok, elapsed = self.runner(job.model, job.prompt, job.tps,
                                              on_token, job.stop_flag)
            with job.lock:
                if job.stop_flag.is_set():
                    job.state = "stopped"
                else:
                    job.answer = text
                    job.tokens_out = ntok or job.tokens_out
                    job.state = "done"
        except Exception as e:
            job.error = str(e)
            job.state = "error"
        finally:
            job.finished = time.time()

    def active(self):
        with self._lock:
            return [j for j in self.jobs if j.state in ("queued", "generating")]

    def result_lines(self):
        """Finished jobs formatted as: > [model] - [answer] [time] [tokens]"""
        out = []
        with self._lock:
            snapshot = list(self.jobs)
        for j in snapshot:
            if j.state == "done" and not getattr(j, "_printed", False):
                j._printed = True
                dur = (j.finished - j.started) if j.started and j.finished else 0
                ans = j.answer.replace("\n", " ").strip()
                if len(ans) > 400:
                    ans = ans[:400] + "…"
                label = f"[{j.number}] {j.model}" if j.number not in ("?", "") else j.model
                out.append(f"> {label} - {ans} [{dur:.1f}s] [{j.tokens_out} tok]")
            elif j.state == "error" and not getattr(j, "_printed", False):
                j._printed = True
                label = f"[{j.number}] {j.model}" if j.number not in ("?", "") else j.model
                out.append(f"> {label} - ERROR: {j.error}")
        return out
