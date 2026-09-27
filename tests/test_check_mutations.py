"""Tests for scripts/check_mutations.py."""

from __future__ import annotations

import importlib.util
import unittest

from test_check_tdd import PY, SCRIPTS, Repo, git

MUTATIONS = SCRIPTS / "check_mutations.py"

spec = importlib.util.spec_from_file_location("check_mutations", MUTATIONS)
cm = importlib.util.module_from_spec(spec)
import sys  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
spec.loader.exec_module(cm)

FEE = "def fee(total):\n    return 0 if total >= 100 else 5\n"
PLAN = """\
# Fee

- Status: Approved

## Acceptance criteria

- AC-1: orders of 100 or more ship free

## Files that change

- src/calc.py
- tests/test_fee.py

## Proof

- AC-1: free from 100 — `{py} tests/test_fee.py`

## Surviving mutants

{accepted}
"""


class MutantGenerationTests(unittest.TestCase):
    def test_operators(self) -> None:
        names = {name for name, _ in cm.mutants_for("    if a >= b and c == 1:")}
        self.assertTrue({">= → >", "and → or", "== → !=", "1 → 2"} <= names)

    def test_skips_comments_imports_and_blank_lines(self) -> None:
        for line in ("# if a == b", "// a == b", "import os", "from x import y", "   "):
            self.assertEqual(cm.mutants_for(line), [], line)

    def test_arrows_and_generics_are_left_alone(self) -> None:
        names = {name for name, _ in cm.mutants_for("const f = (a: List<T>) => a->b;")}
        self.assertFalse(names & {"< → <=", "> → >="})


class CheckMutationsTests(Repo):
    def setup_change(self, test: str, accepted: str = "") -> None:
        self.write("src/calc.py", "def sub(a, b):\n    return a - b\n\n\n" + FEE)
        self.write("tests/test_fee.py", "import sys\nsys.path.insert(0, 'src')\n"
                   "from calc import fee\n" + test)
        self.write("docs/changes/eng-1/plan.md", PLAN.format(py=PY, accepted=accepted))

    def test_strong_tests_kill_every_mutant(self) -> None:
        self.setup_change("assert fee(100) == 0\nassert fee(99) == 5\n")
        res = self.run_script(MUTATIONS)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("survived", res.stdout)  # the summary line
        self.assertNotIn("FAIL", res.stdout)
        self.assertIn(FEE, (self.root / "src/calc.py").read_text())

    def test_weak_tests_leave_survivors(self) -> None:
        self.setup_change("assert fee(150) == 0\n")
        res = self.run_script(MUTATIONS)
        self.assertEqual(res.returncode, 1)
        self.assertIn("FAIL survived  src/calc.py:6", res.stdout)
        self.assertIn(FEE, (self.root / "src/calc.py").read_text())

    def test_listed_survivor_is_accepted(self) -> None:
        self.setup_change("assert fee(150) == 0\n",
                          accepted="- src/calc.py:6 — boundary covered by the checkout e2e suite")
        res = self.run_script(MUTATIONS)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("accepted", res.stdout)

    def test_only_changed_lines_are_mutated(self) -> None:
        self.setup_change("assert fee(150) == 0\n")
        res = self.run_script(MUTATIONS, "--list")
        self.assertEqual(res.returncode, 0)
        self.assertNotIn("src/calc.py:2", res.stdout)  # `a - b` predates the change
        self.assertIn("src/calc.py:6", res.stdout)

    def test_max_limits_the_run(self) -> None:
        self.setup_change("assert fee(150) == 0\n")
        res = self.run_script(MUTATIONS, "--max", "1")
        self.assertIn("not run (raise --max)", res.stdout)

    def test_committed_mode(self) -> None:
        self.setup_change("assert fee(100) == 0\nassert fee(99) == 5\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "fee")
        res = self.run_script(MUTATIONS, "--base", "main")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
