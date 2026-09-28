"""Tests for scripts/check_tdd.py and scripts/check_diff_hygiene.py."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "ai-native-sdlc" / "scripts"
TDD = SCRIPTS / "check_tdd.py"
HYGIENE = SCRIPTS / "check_diff_hygiene.py"
PY = sys.executable

SPEC = """\
# Add

- Status: Approved

## Acceptance criteria

- AC-1: add returns the sum of two numbers
{extra}
"""

PLAN = """\
# Add

- Status: Approved

## Files that change

- src/calc.py
- tests/test_add.py

## Proof

{proof}

## Test changes

{test_changes}
"""

TEST_ADD = """\
import sys
sys.path.insert(0, "src")
from calc import add
assert add(2, 3) == 5
"""


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


class Repo(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "test@example.com")
        git(self.root, "config", "user.name", "Test")
        self.write("src/calc.py", "def sub(a, b):\n    return a - b\n")
        self.write("tests/test_old.py", "import sys\nsys.path.insert(0, 'src')\n"
                   "from calc import sub\nassert sub(3, 1) == 2\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        git(self.root, "switch", "-qc", "feat/eng-1-add")

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def change(self, proof: str | None = None, extra: str = "", test: str = TEST_ADD,
               test_changes: str = "") -> None:
        self.write("src/calc.py", "def sub(a, b):\n    return a - b\n\n\ndef add(a, b):\n    return a + b\n")
        self.write("tests/test_add.py", test)
        self.write("docs/changes/eng-1/spec.md", SPEC.format(extra=extra))
        proof = proof if proof is not None else f"- AC-1: add sums — `{PY} tests/test_add.py`"
        self.write("docs/changes/eng-1/plan.md", PLAN.format(proof=proof, test_changes=test_changes))

    def run_script(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([PY, str(script), *args], cwd=self.root,
                              capture_output=True, text=True)


class CheckTddTests(Repo):
    def test_red_then_green_passes_and_restores_the_tree(self) -> None:
        self.change()
        res = self.run_script(TDD)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("ok   green: AC-1", res.stdout)
        self.assertIn("ok   red:   AC-1", res.stdout)
        self.assertIn("def add", (self.root / "src/calc.py").read_text())
        self.assertTrue((self.root / "tests/test_add.py").is_file())
        self.assertEqual(git(self.root, "stash", "list"), "")

    def test_test_that_passes_without_the_change_fails(self) -> None:
        self.change(test="assert 1 + 1 == 2\n")
        res = self.run_script(TDD)
        self.assertEqual(res.returncode, 1)
        self.assertIn("passes without the change", res.stdout)

    def test_failing_green_fails(self) -> None:
        self.change(test=TEST_ADD.replace("== 5", "== 6"))
        res = self.run_script(TDD)
        self.assertEqual(res.returncode, 1)
        self.assertIn("FAIL green: AC-1", res.stdout)

    def test_uncovered_criterion_fails(self) -> None:
        self.change(extra="- AC-2: add handles negatives")
        res = self.run_script(TDD)
        self.assertEqual(res.returncode, 1)
        self.assertIn("AC-2 has no entry", res.stdout)

    def test_manual_evidence_counts_as_coverage(self) -> None:
        self.change(extra="- AC-2: the result shows in the UI",
                    proof=f"- AC-1: add sums — `{PY} tests/test_add.py`\n"
                          "- AC-2: shown in the UI — manual: screenshot in the MR")
        res = self.run_script(TDD)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("manual evidence expected", res.stdout)

    def test_regression_guard_is_green_only(self) -> None:
        self.change(extra="- AC-2: sub keeps working",
                    proof=f"- AC-1: add sums — `{PY} tests/test_add.py`\n"
                          f"- AC-2: sub kept — regression: `{PY} tests/test_old.py`")
        res = self.run_script(TDD)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("AC-2 is a regression guard", res.stdout)

    def test_unmarked_existing_behavior_fails_red(self) -> None:
        self.change(extra="- AC-2: sub keeps working",
                    proof=f"- AC-1: add sums — `{PY} tests/test_add.py`\n"
                          f"- AC-2: sub kept — `{PY} tests/test_old.py`")
        res = self.run_script(TDD)
        self.assertEqual(res.returncode, 1)
        self.assertIn("AC-2 passes without the change", res.stdout)

    def test_no_criteria_fails(self) -> None:
        self.change()
        self.write("docs/changes/eng-1/spec.md", "# Add\n\n- Status: Approved\n")
        res = self.run_script(TDD)
        self.assertEqual(res.returncode, 1)
        self.assertIn("no acceptance criteria", res.stderr)

    def test_committed_mode_against_base(self) -> None:
        self.change()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "add")
        res = self.run_script(TDD, "--base", "main")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("ok   red:   AC-1", res.stdout)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_committed_mode_needs_a_clean_tree(self) -> None:
        self.change()
        res = self.run_script(TDD, "--base", "main")
        self.assertEqual(res.returncode, 2)
        self.assertIn("clean working tree", res.stderr)


class DiffHygieneTests(Repo):
    def test_clean_change_passes(self) -> None:
        self.change()
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_suppression_without_reason_fails(self) -> None:
        self.change()
        self.write("src/view.ts", "const x: any = load();\n// @ts-ignore\nrender(x);\n")
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 1)
        self.assertEqual(res.stdout.count("type suppression"), 2)

    def test_suppression_with_reason_passes(self) -> None:
        self.change()
        self.write("src/view.ts", "// @ts-expect-error reason: upstream types wrong, see #12\nrender(x);\n")
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_skipped_test_fails(self) -> None:
        self.change(test="import pytest\n\n@pytest.mark.skip\ndef test_add():\n    pass\n")
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 1)
        self.assertIn("skipped or focused test", res.stdout)

    def test_markdown_is_not_scanned(self) -> None:
        self.change()
        self.write("docs/notes.md", "Never use `it.only(` or `# type: ignore` here.\n")
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_rewritten_existing_test_must_be_listed(self) -> None:
        self.change()
        self.write("tests/test_old.py", "assert True\n")
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 1)
        self.assertIn("not listed under ## Test changes: tests/test_old.py", res.stdout)
        self.change(test_changes="- tests/test_old.py — the old expectation contradicted AC-1")
        self.write("tests/test_old.py", "assert True\n")
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_adding_to_an_existing_test_is_fine(self) -> None:
        self.change()
        old = (self.root / "tests/test_old.py").read_text()
        self.write("tests/test_old.py", old + "assert sub(5, 5) == 0\n")
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_deleted_test_file_must_be_listed(self) -> None:
        self.change()
        (self.root / "tests/test_old.py").unlink()
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 1)
        self.assertIn("tests/test_old.py", res.stdout)

    def test_untriaged_learning_fails(self) -> None:
        self.change(test_changes="\n## Learnings\n\n- [ ] gotcha: cache must be cleared in tests")
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 1)
        self.assertIn("learning not triaged", res.stdout)
        self.change(test_changes="\n## Learnings\n\n- [promoted → decisions: docs/adr/0001.md] gotcha: cache\n"
                                 "- [dropped: already documented] convention: naming")
        res = self.run_script(HYGIENE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_committed_mode_against_base(self) -> None:
        self.change()
        self.write("src/view.ts", "const x: any = 1;\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "change")
        res = self.run_script(HYGIENE, "--base", "main")
        self.assertEqual(res.returncode, 1)
        self.assertIn("src/view.ts", res.stdout)


if __name__ == "__main__":
    unittest.main()
