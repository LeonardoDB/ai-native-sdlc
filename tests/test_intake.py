"""Tests for scripts/intake.py (F3 — form/email demand intake)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills" / "ai-native-sdlc" / "scripts" / "intake.py"
)


class IntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: os.system(f"rm -rf {self.tmp}"))
        scripts = self.tmp / "scripts"
        scripts.mkdir()
        shutil.copy2(SCRIPT, scripts / "intake.py")

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.tmp / "scripts" / "intake.py"), *args],
            cwd=self.tmp,
            capture_output=True,
            text=True,
        )

    def test_add_writes_canonical_record(self) -> None:
        details = self.tmp / "details.txt"
        details.write_text("User cannot export expenses.\n", encoding="utf-8")
        res = self.run_cli(
            "add",
            "--source",
            "form",
            "--record-id",
            "form-2026-001",
            "--author",
            "alice",
            "--priority",
            "high",
            "--received-at",
            "2026-09-01T09:00:00Z",
            "--summary",
            "Export is missing.",
            "--details-file",
            str(details),
        )
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        path = self.tmp / "org" / "intake" / "forms" / "form-2026-001.md"
        self.assertTrue(path.is_file())
        content = path.read_text(encoding="utf-8")
        self.assertIn("source: form", content)
        self.assertIn("record_id: form-2026-001", content)
        self.assertIn("received_at: 2026-09-01T09:00:00Z", content)
        self.assertIn("author: alice", content)
        self.assertIn("priority: high", content)
        self.assertIn("## Summary", content)
        self.assertIn("Export is missing.", content)
        self.assertIn("User cannot export expenses.", content)
        self.assertIn("## Status", content)

    def test_duplicate_record_id_rejected(self) -> None:
        res = self.run_cli(
            "add", "--source", "email", "--record-id", "dup-1",
            "--author", "bob", "--summary", "First.",
        )
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        res = self.run_cli(
            "add", "--source", "form", "--record-id", "dup-1",
            "--author", "bob", "--summary", "Second.",
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn("dup-1", res.stderr)

    def test_dry_run_writes_nothing(self) -> None:
        res = self.run_cli(
            "add", "--source", "form", "--record-id", "dry-1",
            "--summary", "Dry.", "--dry-run",
        )
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        self.assertFalse((self.tmp / "org").exists())

    def test_invalid_record_id_and_traversal_rejected(self) -> None:
        res = self.run_cli(
            "add", "--source", "form", "--record-id", "../escape",
            "--summary", "Bad id.",
        )
        self.assertEqual(res.returncode, 1)
        res = self.run_cli(
            "add", "--source", "form", "--record-id", "bad id",
            "--summary", "Bad id.",
        )
        self.assertEqual(res.returncode, 1)
        res = self.run_cli(
            "add", "--source", "form", "--record-id", "safe",
            "--summary", "ok",
            "--output", "../../outside",
        )
        self.assertEqual(res.returncode, 1)

    def test_list_filters_by_source_and_status(self) -> None:
        self.run_cli(
            "add", "--source", "form", "--record-id", "f-1",
            "--summary", "Form demand.",
        )
        self.run_cli(
            "add", "--source", "email", "--record-id", "e-1",
            "--summary", "Email demand.",
        )
        res = self.run_cli("list", "--source", "form")
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        self.assertIn("f-1", res.stdout)
        self.assertNotIn("e-1", res.stdout)
        res = self.run_cli("list", "--status", "new")
        self.assertIn("f-1", res.stdout)
        self.assertIn("e-1", res.stdout)

    def test_validation_errors(self) -> None:
        res = self.run_cli(
            "add", "--source", "slack", "--record-id", "x", "--summary", "Bad source.",
        )
        self.assertEqual(res.returncode, 2)
        res = self.run_cli(
            "add", "--source", "form", "--record-id", "x",
            "--priority", "urgent", "--summary", "Bad priority.",
        )
        self.assertEqual(res.returncode, 2)
        res = self.run_cli("add", "--source", "form", "--record-id", "x")
        self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
