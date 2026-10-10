"""Regression tests: chat context, system prompt, gen options, real metrics, DEMO label."""
import os, sys, time, unittest, threading
sys.path.insert(0, '.')
from tokenpfs.core.chatml import ChatStore
from tokenpfs.core.options import GenOptions
from tokenpfs.core.jobs import Manager


def _tmp_store():
    import tempfile
    return ChatStore(path=os.path.join(tempfile.mkdtemp(), "chat.json"))


class TestChatContext(unittest.TestCase):
    def test_system_and_history_embedded(self):
        c = _tmp_store()
        c.set_system("01", "Отвечай по-русски.")
        c.add("01", "user", "Меня зовут Максим")
        c.add("01", "assistant", "Привет, Максим!")
        p = c.build_prompt("01", "Как меня зовут?")
        self.assertIn("system", p); self.assertIn("Максим", p)
        self.assertIn("Как меня зовут?", p)

    def test_clear_resets_history(self):
        c = _tmp_store(); c.add("02", "user", "x"); c.clear("02")
        self.assertEqual(len(c.history("02")), 0)

    def test_submit_registers_user_turn_once(self):
        import tempfile, os
        c = ChatStore(path=os.path.join(tempfile.mkdtemp(), "chat.json"))
        ev = threading.Event()
        def runner(m, p, tps, on, stop):
            ev.wait(2)   # hold the job so history is inspected mid-flight
            return "ok", 1, 0.05, {"source": "demo", "eval_count": 1}
        jm = Manager(runner=runner)
        jm.submit("01", "m", "вопрос", tps=1000, prompt_full="<ctx>", chat=c)
        jm.submit("01", "m", "второй", tps=1000, prompt_full="<ctx2>", chat=c)
        roles = [t["role"] for t in c.history("01")]
        ev.set()
        self.assertEqual(roles.count("user"), 2)          # no duplicates
        self.assertEqual(roles.count("assistant"), 0)     # turns added once


class TestGenOptions(unittest.TestCase):
    def test_payload_mapping(self):
        o = GenOptions()
        o.set("temperature", "0.9"); o.set("max_tokens", "128")
        pl = o.payload_options()
        self.assertEqual(pl["temperature"], 0.9)
        self.assertEqual(pl["num_predict"], 128)
        self.assertIn("num_ctx", pl); self.assertIn("seed", pl)

    def test_bad_value_rejected(self):
        ok, msg = GenOptions().set("temperature", "abc")
        self.assertFalse(ok); self.assertIn("Not a number", msg)

    def test_out_of_range_rejected(self):
        ok, _ = GenOptions().set("temperature", "5")
        self.assertFalse(ok)


class TestRealMetrics(unittest.TestCase):
    def _wait(self, jm):
        for _ in range(60):
            l = jm.result_lines()
            if l: return l[0]
            time.sleep(0.05)
        self.fail("no result")

    def test_ollama_eval_count_used(self):
        def runner(m, p, tps, on, stop):
            text = "ответ"
            on(text)
            st = {"source": "ollama", "eval_count": 57,
                  "eval_duration_us": 1_140_000, "real_tps": 50.0}
            return text, 3, 0.5, st
        line = self._wait_line(runner)
        self.assertIn("[57 tok]", line)       # honest count from Ollama
        self.assertIn("(ollama)", line)
        self.assertNotIn("[DEMO]", line)

    def test_demo_label_present(self):
        def runner(m, p, tps, on, stop):
            st = {"source": "demo", "eval_count": 3, "real_tps": 0.0}
            return "demo text", 3, 0.1, st
        line = self._wait_line(runner)
        self.assertIn("[DEMO]", line)

    def _wait_line(self, runner):
        jm = Manager(runner=runner)
        jm.submit("01", "model", "q", tps=1000, prompt_full="q", chat=None)
        for _ in range(60):
            l = jm.result_lines()
            if l: return l[0]
            time.sleep(0.05)
        self.fail("no result")


if __name__ == "__main__":
    unittest.main(verbosity=2)
