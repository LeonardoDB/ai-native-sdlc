"""Tests for scripts/check_plan_sync.py (deterministic plan-sync)."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills" / "ai-native-sdlc" / "scripts" / "check_plan_sync.py"
)

PLAN_PATH = "docs/changes/eng-1/plan.md"

PLAN = """\
# Feature

- Status: Approved

## Files that change

{files}

## Proof

- tests cover it.
"""


class PlanSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: os.system(f"rm -rf {self.root}"))
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "test@example.com")
        git(self.root, "config", "user.name", "Test")

    def commit(self, message: str) -> None:
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", message)

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
        )

    def initial_commit(self) -> None:
        self.write("src/base.py", "BASE = 1\n")
        self.commit("base")

    def pr(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_cli("--base", "HEAD~1", "--head", "HEAD", *extra)

    def test_process_only_changes_pass_without_plan(self) -> None:
        self.initial_commit()
        self.write("docs/note.md", "# note\n")
        self.write("README.md", "readme\n")
        self.write(".gitlab/merge_request_templates/default.md", "tmpl\n")
        self.commit("docs only")
        res = self.pr()
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_missing_plan_fails(self) -> None:
        self.initial_commit()
        self.write("src/new.py", "NEW = 1\n")
        self.commit("code without plan")
        res = self.pr()
        self.assertEqual(res.returncode, 1)
        self.assertIn("docs/changes/<task>/plan.md", res.stderr)

    def test_draft_plan_fails(self) -> None:
        self.initial_commit()
        self.write("src/new.py", "NEW = 1\n")
        self.write(PLAN_PATH, PLAN.format(files="- src/new.py").replace("Approved", "Draft"))
        self.commit("draft plan")
        res = self.pr()
        self.assertEqual(res.returncode, 1)
        self.assertIn("not approved", res.stderr.lower())

    def test_planned_files_pass(self) -> None:
        self.initial_commit()
        self.write("src/new.py", "NEW = 1\n")
        self.write(PLAN_PATH, PLAN.format(files="- src/new.py"))
        self.commit("planned change")
        res = self.pr()
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_delegated_approval_passes(self) -> None:
        self.initial_commit()
        self.write("src/new.py", "NEW = 1\n")
        plan = PLAN.format(files="- src/new.py").replace(
            "- Status: Approved\n", "- Status: Approved\n- Approved-by: delegated (2026-10-02)\n")
        self.write(PLAN_PATH, plan)
        self.commit("delegated plan")
        res = self.pr()
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_unplanned_file_fails(self) -> None:
        self.initial_commit()
        self.write("src/new.py", "NEW = 1\n")
        self.write("src/extra.py", "EXTRA = 1\n")
        self.write(PLAN_PATH, PLAN.format(files="- src/new.py"))
        self.commit("unplanned change")
        res = self.pr()
        self.assertEqual(res.returncode, 1)
        self.assertIn("unplanned", res.stderr.lower())
        self.assertIn("src/extra.py", res.stderr)

    def test_plan_diff_adding_matching_entry_passes(self) -> None:
        self.initial_commit()
        self.write(PLAN_PATH, PLAN.format(files="- src/base.py"))
        self.commit("plan")
        self.write("src/new.py", "NEW = 1\n")
        self.write(PLAN_PATH, PLAN.format(files="- src/base.py\n- src/new.py"))
        self.commit("declare departure in plan")
        res = self.pr()
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_unrelated_plan_edit_does_not_exempt_file(self) -> None:
        self.initial_commit()
        self.write(PLAN_PATH, PLAN.format(files="- src/base.py"))
        self.commit("plan")
        self.write("src/new.py", "NEW = 1\n")
        self.write(PLAN_PATH, PLAN.format(files="- src/base.py").replace(
            "## Proof", "## Proof\n\nEdited prose only."))
        self.commit("prose-only plan change")
        res = self.pr()
        self.assertEqual(res.returncode, 1)
        self.assertIn("unplanned", res.stderr.lower())

    def test_glob_entry_matches_file(self) -> None:
        self.initial_commit()
        self.write("src/util/helper.py", "HELPER = 1\n")
        self.write(PLAN_PATH, PLAN.format(files="- src/util/*.py"))
        self.commit("globbed change")
        res = self.pr()
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_another_tasks_plan_is_not_used(self) -> None:
        self.write("docs/changes/eng-0/plan.md", PLAN.format(files="- src/*"))
        self.initial_commit()
        self.write("src/new.py", "NEW = 1\n")
        self.commit("code relying on an old plan")
        res = self.pr()
        self.assertEqual(res.returncode, 1)
        self.assertIn("no plan", res.stderr)

    def test_several_plans_need_explicit_plan(self) -> None:
        self.initial_commit()
        self.write("src/new.py", "NEW = 1\n")
        self.write(PLAN_PATH, PLAN.format(files="- src/new.py"))
        self.write("docs/changes/eng-2/plan.md", PLAN.format(files="- other/*"))
        self.commit("two plans")
        res = self.pr()
        self.assertEqual(res.returncode, 2)
        self.assertIn("--plan", res.stderr)
        res = self.pr("--plan", PLAN_PATH)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_hook_mode_uses_staged_plan(self) -> None:
        self.initial_commit()
        self.write("src/new.py", "NEW = 1\n")
        self.write(PLAN_PATH, PLAN.format(files="- src/new.py"))
        git(self.root, "add", "-A")
        res = self.run_cli("--hook")
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_hook_mode_finds_plan_from_branch_name(self) -> None:
        self.initial_commit()
        git(self.root, "switch", "-qc", "feat/eng-1-csv-export")
        self.write(PLAN_PATH, PLAN.format(files="- src/new.py"))
        self.commit("plan first")
        self.write("src/new.py", "NEW = 1\n")
        git(self.root, "add", "src/new.py")
        res = self.run_cli("--hook")
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        self.write("src/extra.py", "EXTRA = 1\n")
        git(self.root, "add", "src/extra.py")
        res = self.run_cli("--hook")
        self.assertEqual(res.returncode, 1)
        self.assertIn("unplanned", res.stderr.lower())

    def test_hook_mode_without_any_plan_fails(self) -> None:
        self.initial_commit()
        git(self.root, "switch", "-qc", "feat/eng-9-other")
        self.write("src/new.py", "NEW = 1\n")
        git(self.root, "add", "src/new.py")
        res = self.run_cli("--hook")
        self.assertEqual(res.returncode, 1)
        self.assertIn("no plan", res.stderr)

    def test_hook_mode_draft_staged_plan_fails(self) -> None:
        self.initial_commit()
        self.write("src/new.py", "NEW = 1\n")
        self.write(PLAN_PATH, PLAN.format(files="- src/new.py").replace("Approved", "Draft"))
        git(self.root, "add", "-A")
        res = self.run_cli("--hook")
        self.assertEqual(res.returncode, 1)
        self.assertIn("not approved", res.stderr.lower())


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
