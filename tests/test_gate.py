"""Tests for hooks/gate.py (the PreToolUse gate)."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from test_check_tdd import PY, Repo, git

GATE = Path(__file__).resolve().parent.parent / "skills" / "ai-native-sdlc" / "hooks" / "gate.py"


class GateTests(Repo):
    def gate(self, command: str, tool: str = "Bash") -> subprocess.CompletedProcess[str]:
        event = {"hook_event_name": "PreToolUse", "tool_name": tool,
                 "tool_input": {"command": command}, "cwd": str(self.root)}
        return subprocess.run([PY, str(GATE)], input=json.dumps(event),
                              capture_output=True, text=True)

    def committed_change(self, test: str | None = None) -> None:
        if test is None:
            self.change()
        else:
            self.change(test=test)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "feat: add (ENG-1)")

    def test_merge_is_always_blocked(self) -> None:
        for command in ("glab mr merge 12", "gh pr merge 3 --squash", "cd x && glab mr merge"):
            res = self.gate(command)
            self.assertEqual(res.returncode, 2, command)
            self.assertIn("outside this workflow", res.stderr)

    def test_no_verify_and_bare_force_are_blocked(self) -> None:
        self.assertEqual(self.gate("git commit --no-verify -m x").returncode, 2)
        self.assertEqual(self.gate("git push -f origin feat/eng-1-add").returncode, 2)
        self.assertEqual(self.gate("git push --force origin feat/eng-1-add").returncode, 2)

    def test_push_to_default_branch_is_blocked(self) -> None:
        for command in ("git push origin main", "git push origin HEAD:main"):
            res = self.gate(command)
            self.assertEqual(res.returncode, 2, command)
            self.assertIn("default branch", res.stderr)

    def test_unrelated_commands_and_tools_pass(self) -> None:
        self.assertEqual(self.gate("git status").returncode, 0)
        self.assertEqual(self.gate("python3 -m pytest").returncode, 0)
        self.assertEqual(self.gate("glab mr merge 1", tool="Read").returncode, 0)

    def test_branch_without_a_task_plan_is_left_alone(self) -> None:
        git(self.root, "switch", "-qc", "chore/bump")
        self.assertEqual(self.gate("git push -u origin chore/bump").returncode, 0)

    def test_publish_with_passing_checks_is_allowed(self) -> None:
        self.committed_change()
        res = self.gate("git push -u origin feat/eng-1-add")
        self.assertEqual(res.returncode, 0, res.stderr)
        res = self.gate("git push --force-with-lease origin feat/eng-1-add")
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_publish_with_failing_checks_is_blocked(self) -> None:
        self.committed_change(test="assert 1 + 1 == 2\n")  # passes without the change
        res = self.gate("glab mr create --fill")
        self.assertEqual(res.returncode, 2)
        self.assertIn("check_tdd.py", res.stderr)

    def test_publish_with_a_dirty_tree_is_blocked(self) -> None:
        self.change()
        res = self.gate("gh pr create --fill")
        self.assertEqual(res.returncode, 2)
        self.assertIn("working tree is not clean", res.stderr)

    def test_malformed_event_never_blocks(self) -> None:
        res = subprocess.run([PY, str(GATE)], input="not json", capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)


if __name__ == "__main__":
    unittest.main()
