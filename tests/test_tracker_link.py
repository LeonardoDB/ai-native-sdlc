"""Tests for scripts/tracker_link.py (offline; no tracker access required)."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills" / "ai-native-sdlc" / "scripts" / "tracker_link.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("tracker_link", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tl = _load_module()

REPO = {"remote": "git@gitlab.acme.com.br:squad/pay/api.git", "host": "gitlab.acme.com.br",
        "project": "squad/pay/api", "forge": "gitlab"}


class ParseTests(unittest.TestCase):
    def test_self_hosted_gitlab_needs_no_config(self) -> None:
        result, error = tl.parse("https://gitlab.acme.com.br/squad/pay/api/-/issues/42", REPO)
        self.assertIsNone(error)
        self.assertEqual(result["system"], "gitlab")
        self.assertEqual(result["kind"], "issue")
        self.assertEqual(result["ref"], "squad/pay/api#42")
        self.assertTrue(result["repo_matches"])
        self.assertEqual(result["slug"], "42")
        self.assertEqual(result["change_dir"], "docs/changes/42")

    def test_gitlab_on_non_gitlab_hostname(self) -> None:
        result, error = tl.parse("https://code.acme.io/team/app/-/work_items/7")
        self.assertIsNone(error)
        self.assertEqual(result["system"], "gitlab")
        self.assertEqual(result["ref"], "team/app#7")
        self.assertIsNone(result["repo_matches"])

    def test_ssh_host_alias_still_matches(self) -> None:
        alias = tl.parse_remote("git@gitlab-work:squad/pay/api.git")
        result, error = tl.parse("https://gitlab.acme.com.br/squad/pay/api/-/issues/42", alias)
        self.assertIsNone(error)
        self.assertTrue(result["repo_matches"])

    def test_gitlab_task_from_another_project(self) -> None:
        result, error = tl.parse("https://gitlab.acme.com.br/squad/web/-/issues/3", REPO)
        self.assertIsNone(error)
        self.assertFalse(result["repo_matches"])
        self.assertEqual(result["slug"], "web-3")

    def test_gitlab_board_epic_and_mr_are_rejected(self) -> None:
        for url, kind in (
            ("https://gitlab.acme.com.br/groups/squad/-/boards/3", "board"),
            ("https://gitlab.acme.com.br/groups/squad/-/epics/5", "epic"),
            ("https://gitlab.acme.com.br/squad/api/-/merge_requests/9", "merge_request"),
        ):
            result, error = tl.parse(url)
            self.assertEqual(result["kind"], kind)
            self.assertIn("not a task", error)
        board, _ = tl.parse("https://gitlab.acme.com.br/groups/squad/-/boards/3")
        self.assertEqual(board["project"], "squad")

    def test_linear_issue_with_slug(self) -> None:
        result, error = tl.parse("https://linear.app/acme/issue/eng-123/add-csv-export", REPO)
        self.assertIsNone(error)
        self.assertEqual(result["system"], "linear")
        self.assertEqual(result["ref"], "ENG-123")
        self.assertEqual(result["project"], "ENG")
        self.assertIsNone(result["repo_matches"])
        self.assertEqual(result["change_dir"], "docs/changes/eng-123")
        self.assertEqual(result["current_repo"], REPO)

    def test_linear_board_is_rejected(self) -> None:
        result, error = tl.parse("https://linear.app/acme/team/ENG/active")
        self.assertEqual(result["kind"], "board")
        self.assertIsNotNone(error)

    def test_github_issue_and_project(self) -> None:
        result, error = tl.parse("github.com/acme/app/issues/12")
        self.assertIsNone(error)
        self.assertEqual(result["ref"], "acme/app#12")
        board, error = tl.parse("https://github.com/orgs/acme/projects/2")
        self.assertEqual(board["kind"], "board")
        self.assertIsNotNone(error)

    def test_unrecognized_link(self) -> None:
        result, error = tl.parse("https://jira.acme.com/browse/X-1")
        self.assertIsNone(result)
        self.assertIn("unrecognized link", error)

    def test_non_http_link(self) -> None:
        result, error = tl.parse("ftp://gitlab.com/a/b/-/issues/1")
        self.assertIsNone(result)
        self.assertIn("http", error)


class RemoteTests(unittest.TestCase):
    def test_scp_and_https_remotes(self) -> None:
        self.assertEqual(tl.parse_remote("git@gitlab.acme.com.br:squad/pay/api.git"), REPO)
        https = tl.parse_remote("https://github.com/acme/app.git\n")
        self.assertEqual((https["host"], https["project"], https["forge"]),
                         ("github.com", "acme/app", "github"))
        ssh_url = tl.parse_remote("ssh://git@code.acme.io:2222/team/app.git")
        self.assertEqual((ssh_url["host"], ssh_url["project"], ssh_url["forge"]),
                         ("code.acme.io", "team/app", None))

    def test_unparseable_remote(self) -> None:
        self.assertIsNone(tl.parse_remote("not a remote"))


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "remote", "add", "origin",
                        "git@gitlab.acme.com.br:squad/api.git"], check=True)

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = tl.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_parse_reads_current_repo(self) -> None:
        code, out, _ = self.run_cli(
            "parse", "https://gitlab.acme.com.br/squad/api/-/issues/42", "--repo-dir", str(self.repo))
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["ref"], "squad/api#42")
        self.assertEqual(data["current_repo"]["forge"], "gitlab")
        self.assertTrue(data["repo_matches"])

    def test_outside_a_repo(self) -> None:
        with tempfile.TemporaryDirectory() as plain:
            code, out, _ = self.run_cli(
                "parse", "https://linear.app/acme/issue/ENG-1", "--repo-dir", plain)
        self.assertEqual(code, 0)
        self.assertIsNone(json.loads(out)["current_repo"])

    def test_board_exits_1_but_prints_json(self) -> None:
        code, out, err = self.run_cli(
            "parse", "https://gitlab.acme.com.br/squad/api/-/boards/1", "--repo-dir", str(self.repo))
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["kind"], "board")
        self.assertIn("not a task", err)

    def test_unrecognized_exits_1(self) -> None:
        code, out, err = self.run_cli("parse", "https://jira.acme.com/browse/X-1")
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("unrecognized link", err)


if __name__ == "__main__":
    unittest.main()
