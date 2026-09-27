"""Tests for scripts/metrics.py."""

from __future__ import annotations

import json
import os
import stat
import subprocess

from test_check_tdd import PY, SCRIPTS, Repo, git

METRICS = SCRIPTS / "metrics.py"

PLAN = """\
# T

- Status: Approved

## Acceptance criteria

- AC-1: one
- AC-2: two

## Proof

- AC-1: one — `true`
- AC-2: two — manual: screenshot

## Test changes

- tests/test_old.py — contradicted AC-1

## Surviving mutants

## Deviations

- renamed helper
- extra file

## Review

### Round 1

- fixed src/a.py:3

### Round 2

- clean
"""


class MetricsTests(Repo):
    def commit(self, message: str, when: int) -> None:
        env = {**os.environ, "GIT_AUTHOR_DATE": f"{when} +0000", "GIT_COMMITTER_DATE": f"{when} +0000"}
        subprocess.run(["git", "-C", str(self.root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", message], check=True, env=env)

    def build_history(self) -> None:
        day = 86400
        self.write("docs/changes/eng-1/spec.md", "# T\n\n## Acceptance criteria\n\n- AC-1: one\n- AC-2: two\n")
        self.commit("spec", 1_700_000_000)
        self.write("docs/changes/eng-1/plan.md", PLAN)
        self.commit("plan", 1_700_000_000 + day)
        self.write("docs/changes/eng-1/spec.md", "# T\n\n## Acceptance criteria\n\n- AC-1: one!\n- AC-2: two\n")
        self.commit("spec changed while building", 1_700_000_000 + 2 * day)
        self.write("docs/changes/eng-1/plan.md", PLAN + "\n")
        self.commit("plan edit", 1_700_000_000 + 3 * day)
        self.write("docs/changes/9/plan.md", "# L\n\n- Status: Approved\n\n## Acceptance criteria\n\n- AC-1: x\n")
        self.commit("light task", 1_700_000_000 + 3 * day)

    def test_task_metrics(self) -> None:
        self.build_history()
        res = subprocess.run([PY, str(METRICS), "--json"], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        full = next(t for t in data["tasks"] if t["task"] == "eng-1")
        self.assertEqual(full["path"], "full")
        self.assertEqual(full["criteria"], 2)
        self.assertEqual(full["manual_criteria"], 1)
        self.assertEqual(full["spec_rework"], 1)
        self.assertEqual(full["plan_edits"], 1)
        self.assertEqual(full["review_rounds"], 2)
        self.assertEqual(full["deviations"], 2)
        self.assertEqual(full["test_changes"], 1)
        self.assertEqual(full["survivors"], 0)
        self.assertEqual(full["lead_days"], 3.0)
        light = next(t for t in data["tasks"] if t["task"] == "9")
        self.assertEqual(light["path"], "light")
        self.assertEqual(data["summary"]["tasks"], 2)
        self.assertEqual(data["summary"]["full_path_share"], 0.5)
        self.assertEqual(data["summary"]["spec_rework_share"], 0.5)

    def test_table_and_multiple_repos(self) -> None:
        self.build_history()
        res = subprocess.run([PY, str(METRICS), "--repos", str(self.root), "/nonexistent"],
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("| eng-1 | full |", res.stdout.replace(f"| {self.root.name} ", "| "))
        self.assertIn("mean_review_rounds: 1", res.stdout)

    def test_forge_data_from_gh(self) -> None:
        self.build_history()
        git(self.root, "remote", "add", "origin", "https://github.com/acme/app.git")
        bin_dir = self.root / "fakebin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text("#!/bin/sh\necho '[{\"number\": 7, \"headRefName\": \"feat/eng-1-x\", "
                      "\"createdAt\": \"2026-01-01T00:00:00Z\", \"mergedAt\": \"2026-01-03T12:00:00Z\", "
                      "\"comments\": [{}, {}, {}]}]'\n")
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
        res = subprocess.run([PY, str(METRICS), "--forge", "--json"], cwd=self.root,
                             capture_output=True, text=True, env=env)
        full = next(t for t in json.loads(res.stdout)["tasks"] if t["task"] == "eng-1")
        self.assertEqual((full["mr"], full["mr_comments"], full["mr_days"]), ("#7", 3, 2.5))

    def test_no_tasks(self) -> None:
        res = subprocess.run([PY, str(METRICS)], cwd=self.root, capture_output=True, text=True)
        self.assertIn("no tasks found", res.stdout)
