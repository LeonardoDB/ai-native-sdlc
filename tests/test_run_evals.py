#!/usr/bin/env python3
"""Unit tests for scripts/run_evals.py."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills/ai-native-sdlc/scripts"))
import run_evals  # noqa: E402


def write_eval(evals_dir: str, name: str, data: dict) -> None:
    with open(os.path.join(evals_dir, f"{name}.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh)


class RunEvalsTests(unittest.TestCase):
    def _dir_with_good_and_bad(self) -> str:
        td = tempfile.mkdtemp()
        evals = os.path.join(td, "evals")
        os.makedirs(evals)
        write_eval(evals, "good", {"name": "good", "checks": ["true", {"run": "echo hi", "contains": "hi"}]})
        write_eval(evals, "bad", {"name": "bad", "checks": ["false"]})
        return evals

    def test_pass_rate_and_exit_codes(self):
        evals = self._dir_with_good_and_bad()
        self.addCleanup(lambda: os.system(f"rm -rf {os.path.dirname(evals)}"))
        self.assertEqual(run_evals.main([evals, "--min-pass-rate", "0.5"]), 0)  # 2/3 >= 0.5
        self.assertEqual(run_evals.main([evals, "--min-pass-rate", "0.8"]), 1)  # 2/3 < 0.8

    def test_contains_check_and_100_percent(self):
        td = tempfile.mkdtemp()
        evals = os.path.join(td, "evals")
        os.makedirs(evals)
        self.addCleanup(lambda: os.system(f"rm -rf {td}"))
        write_eval(evals, "contains", {"checks": [{"run": "echo hello", "contains": "hello"}]})
        self.assertEqual(run_evals.main([evals, "--min-pass-rate", "1.0"]), 0)

    def test_record_writes_jsonl(self):
        evals = self._dir_with_good_and_bad()
        td = os.path.dirname(evals)
        self.addCleanup(lambda: os.system(f"rm -rf {td}"))
        run_evals.main([evals, "--record", "--record-dir", os.path.join(td, "results")])
        rec_path = os.path.join(td, "results", "results.jsonl")
        self.assertTrue(os.path.exists(rec_path))
        with open(rec_path, encoding="utf-8") as fh:
            rec = json.loads(fh.readline())
        self.assertEqual(rec["passed"], 2)
        self.assertEqual(rec["total"], 3)

    def test_no_evals_returns_2(self):
        td = tempfile.mkdtemp()
        self.addCleanup(lambda: os.system(f"rm -rf {td}"))
        self.assertEqual(run_evals.main([td]), 2)


if __name__ == "__main__":
    unittest.main()
