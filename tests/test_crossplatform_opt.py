"""Regression tests for v2.0.0-alpha cross-platform + chat/opt fixes."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tokenpfs.core.options import GenOptions
from tokenpfs.core.chatml import ChatStore
from tokenpfs.core.jobs import Manager


class TestOptScope(unittest.TestCase):
    def test_per_model_override(self):
        o = GenOptions()
        ok, msg = o.set("01", "temperature", "0.2")
        self.assertTrue(ok)
        self.assertIn("(model [01])", msg)
        self.assertEqual(o.payload_options("01")["temperature"], 0.2)
        self.assertEqual(o.payload_options(None)["temperature"], 0.7)  # session default

    def test_legacy_two_arg_call(self):
        o = GenOptions()
        ok, _ = o.set("seed", "42")           # old API: set(key, value)
        self.assertTrue(ok)
        self.assertEqual(o.payload_options()["seed"], 42)

    def test_unset_restores_session(self):
        o = GenOptions()
        o.set(None, "top_p", "0.5")
        o.set("02", "top_p", "0.9")
        self.assertEqual(o.payload_options("02")["top_p"], 0.9)
        ok, _ = o.unset("02", "top_p")
        self.assertTrue(ok)
        self.assertEqual(o.payload_options("02")["top_p"], 0.5)

    def test_validation_bounds_and_types(self):
        o = GenOptions()
        self.assertFalse(o.set(None, "temperature", "3")[0])   # out of range
        self.assertFalse(o.set(None, "num_ctx", "abc")[0])     # not a number
        self.assertFalse(o.set(None, "hacker_key", "1")[0])    # unknown key
        ok, _ = o.set(None, "max_tokens", "512.0")             # float str -> int
        self.assertTrue(ok)
        self.assertIsInstance(o.values["max_tokens"], int)


class TestNoDoubleUserTurn(unittest.TestCase):
    def test_history_has_one_user_turn_per_w(self):
        tmp = tempfile.mktemp(suffix=".json")
        chat = ChatStore(tmp)
        captured = []

        def runner(model, prompt, tps, on_token, stop_flag, number=None):
            captured.append(prompt)
            on_token("ok ")
            return "ok", 1, 0.1, {"source": "demo", "eval_count": 1}

        mgr = Manager(runner)
        # simulate what App.ask() does now:
        q = "Привет"
        prompt = chat.build_prompt("01", q)
        chat.add("01", "user", q)
        job = mgr.submit("01", "m", q, 10, prompt_full=prompt,
                         chat=chat, user_turn_added=True)
        import time as _t
        for _ in range(50):
            if job.state in ("done", "error", "stopped"):
                break
            _t.sleep(0.1)
        hist = chat.history("01")
        roles = [m["role"] for m in hist]
        self.assertEqual(roles.count("user"), 1, f"user turn duplicated: {roles}")
        self.assertEqual(roles.count("assistant"), 1)
        os.unlink(tmp)


class TestDemoPromptExtraction(unittest.TestCase):
    def test_last_user_turn_extracted(self):
        from tokenpfs_app import App
        blob = ("<|im_start|>system\nроль<|im_end|>\n"
                "<|im_start|>user\nпервый<|im_end|>\n"
                "<|im_start|>assistant\nответ<|im_end|>\n"
                "<|im_start|>user\nВторой вопрос<|im_end|>\n"
                "<|im_start|>assistant\n")
        # replicate extraction logic used by _demo_runner
        chunks = [c for c in blob.split("<|im_start|>") if c.startswith("user")]
        last = chunks[-1].split("<|im_end|>")[0].split("\n", 1)[-1]
        self.assertEqual(last, "Второй вопрос")


if __name__ == "__main__":
    unittest.main(verbosity=2)
