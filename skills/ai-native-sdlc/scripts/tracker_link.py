#!/usr/bin/env python3
"""Resolve a tracker task link (Linear, GitLab, GitHub) against the current repo.

The intent lives in the tracker: a task on the board is an accepted intent.
This script is the deterministic first step of starting work from a link —
it identifies the system, the kind of link, and the native task reference,
and compares the link with the repository the agent is working in. It needs
no configuration and never calls the network; the agent reads the task
itself (MCP connector or CLI) once the system is known.

Detection is by link shape, so self-hosted instances need no setup:
    linear.app/<workspace>/issue/<KEY-123>        -> linear
    <any host>/<namespace>/<project>/-/issues/42  -> gitlab (the /-/ separator)
    github.com/<owner>/<repo>/issues/42           -> github

The repo is the one you are in (`git remote get-url origin`), as in any
forge-aware tool. `repo_matches` compares project paths (not hosts, so SSH
host aliases still match) and is false when a GitLab/GitHub task belongs
to a different project than the current checkout — ask before switching or
before working cross-project. Linear tasks carry no repo, so it is null.

Usage:
    tracker_link.py parse <url> [--repo-dir .]

Output: one JSON object on stdout:
    system        linear | gitlab | github
    kind          issue | merge_request | board | epic | project | unknown
                  (a merge_request link starts the MR/PR feedback flow)
    host          link host (lowercase)
    ref           native reference for commits and MRs/PRs
                  (ENG-123, group/project#42, owner/repo#42), null if not a task
    id            task number or key, null if not a task
    project       GitLab namespace path, GitHub owner/repo, or Linear team key
    slug          short task id for folders and branches: eng-123 (Linear), 42
                  (a task of the current repo), backlog-42 (another project)
    change_dir    docs/changes/<slug> — where the task's spec.md and plan.md go
    url           the normalized link
    current_repo  {remote, host, project, forge, root, branch, default_branch,
                  dirty} of --repo-dir, or null outside a repo with an origin
    repo_matches  true | false | null (unknown, or a Linear task)
    on_task_branch  true when the checked-out branch belongs to this task
                  (its last segment is the slug or starts with "<slug>-")
    state         where the task stands, read from change_dir in the repo:
                  {spec, plan: missing | draft | approved, next} with next one
                  of design, approve-spec, plan, approve-plan, shape, implement — so a
                  second run with the same link resumes instead of restarting

Exit codes: 0 = task or MR/PR link resolved, 1 = another kind of link or unrecognized
(JSON still printed when the system is known), 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_tdd as tdd  # noqa: E402

LINEAR_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)-(\d+)$")
SCP_REMOTE_RE = re.compile(r"^(?:[^@/]+@)?([^:/]+):(.+)$")
STATUS_APPROVED_RE = re.compile(r"(?im)^\s*[-*]\s*Status\s*:\s*Approved\s*$")


def _result(system: str, kind: str, host: str, url: str, **fields) -> dict:
    out = {"system": system, "kind": kind, "host": host, "ref": None, "id": None,
           "project": None, "url": url}
    out.update(fields)
    return out


def _parse_gitlab(host: str, segments: list[str], url: str) -> dict:
    split = segments.index("-")
    namespace, rest = segments[:split], segments[split + 1:]
    if namespace[:1] == ["groups"]:
        namespace = namespace[1:]
    project = "/".join(namespace) or None
    section = rest[0] if rest else ""
    number = rest[1] if len(rest) > 1 and rest[1].isdigit() else None
    kinds = {"issues": "issue", "work_items": "issue", "boards": "board",
             "epics": "epic", "merge_requests": "merge_request"}
    kind = kinds.get(section, "unknown")
    if kind == "issue" and (number is None or project is None):
        kind = "unknown"
    if kind == "merge_request" and number and project:
        return _result("gitlab", kind, host, url, ref=f"{project}!{number}", id=number,
                       project=project)
    if kind != "issue":
        return _result("gitlab", kind, host, url, project=project)
    return _result("gitlab", "issue", host, url, ref=f"{project}#{number}", id=number,
                   project=project)


def _parse_github(host: str, segments: list[str], url: str) -> dict:
    if len(segments) >= 3 and segments[0] in ("orgs", "users") and segments[2] == "projects":
        return _result("github", "board", host, url, project=segments[1])
    if len(segments) < 4:
        return _result("github", "unknown", host, url)
    project = f"{segments[0]}/{segments[1]}"
    section, number = segments[2], segments[3]
    if section == "projects":
        return _result("github", "board", host, url, project=project)
    if section == "pull" and number.isdigit():
        return _result("github", "merge_request", host, url, ref=f"{project}#{number}",
                       id=number, project=project)
    if section != "issues" or not number.isdigit():
        return _result("github", "unknown", host, url, project=project)
    return _result("github", "issue", host, url, ref=f"{project}#{number}", id=number,
                   project=project)


def _parse_linear(host: str, segments: list[str], url: str) -> dict:
    # linear.app/<workspace>/issue/<KEY-123>[/<slug>]
    section = segments[1] if len(segments) > 1 else ""
    if section == "issue" and len(segments) > 2:
        match = LINEAR_KEY_RE.match(segments[2])
        if match:
            key = segments[2].upper()
            return _result("linear", "issue", host, url, ref=key, id=key,
                           project=match.group(1).upper())
    kinds = {"team": "board", "view": "board", "project": "project"}
    return _result("linear", kinds.get(section, "unknown"), host, url)


def parse_remote(remote: str) -> dict | None:
    """Split a git remote (https or scp-style ssh) into host and project path."""
    remote = remote.strip()
    if "://" in remote:
        parts = urlsplit(remote)
        host, path = (parts.hostname or "").lower(), parts.path
    else:
        match = SCP_REMOTE_RE.match(remote)
        if not match:
            return None
        host, path = match.group(1).lower(), match.group(2)
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    if not host or not path:
        return None
    forge = "github" if "github" in host else "gitlab" if "gitlab" in host else None
    return {"remote": remote, "host": host, "project": path, "forge": forge}


def _git(repo_dir: str, *args: str) -> str | None:
    try:
        res = subprocess.run(["git", "-C", repo_dir, *args],
                             capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    return res.stdout.strip() if res.returncode == 0 else None


def current_repo(repo_dir: str) -> dict | None:
    remote = _git(repo_dir, "remote", "get-url", "origin")
    repo = parse_remote(remote) if remote else None
    if repo is None:
        return None
    head = _git(repo_dir, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    repo.update({
        "root": _git(repo_dir, "rev-parse", "--show-toplevel"),
        "branch": _git(repo_dir, "branch", "--show-current") or None,
        "default_branch": head.split("/", 1)[1] if head and "/" in head else None,
        "dirty": bool(_git(repo_dir, "status", "--porcelain")),
    })
    return repo


def _artifact_status(path: Path) -> str:
    if not path.is_file():
        return "missing"
    return "approved" if STATUS_APPROVED_RE.search(path.read_text(encoding="utf-8")) else "draft"


def task_state(root: str, change_dir: str) -> dict:
    """Where a task stands, from its spec.md and plan.md (the light path has no spec)."""
    base = Path(root) / change_dir
    spec, plan = _artifact_status(base / "spec.md"), _artifact_status(base / "plan.md")
    if plan == "approved":
        plan_text = (base / "plan.md").read_text(encoding="utf-8")
        step = "shape" if tdd.shape_status(plan_text) == "pending" else "implement"
    elif plan == "draft":
        step = "approve-plan"
    elif spec == "approved":
        step = "plan"
    elif spec == "draft":
        step = "approve-spec"
    else:
        step = "design"
    return {"spec": spec, "plan": plan, "next": step}


def parse(url: str, repo: dict | None = None) -> tuple[dict | None, str | None]:
    """Return (result, error). result is None only when the link is unrecognized."""
    raw = url.strip()
    if "://" not in raw:
        raw = "https://" + raw
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None, f"not an http(s) link: {url!r}"
    host = parts.hostname.lower()
    segments = [s for s in parts.path.split("/") if s]
    normalized = f"{parts.scheme}://{host}{('/' + '/'.join(segments)) if segments else ''}"

    if host == "linear.app":
        result = _parse_linear(host, segments, normalized)
    elif "-" in segments:
        result = _parse_gitlab(host, segments, normalized)
    elif host == "github.com":
        result = _parse_github(host, segments, normalized)
    else:
        return None, (f"unrecognized link {url!r}: expected a Linear task, a GitLab "
                      "task (…/-/issues/N on any host), or a GitHub issue")

    result["current_repo"] = repo
    result["repo_matches"] = None
    if repo and result["system"] != "linear" and result["project"]:
        # Project path only: SSH host aliases (git@gitlab-work:group/app.git)
        # make the remote host differ from the link host for the same repo.
        result["repo_matches"] = repo["project"].lower() == result["project"].lower()
    result["slug"] = result["change_dir"] = None
    if result["kind"] == "issue":
        if result["system"] == "linear" or result["repo_matches"]:
            slug = str(result["id"]).lower()
        else:
            slug = f"{result['project'].rsplit('/', 1)[-1].lower()}-{result['id']}"
        result["slug"] = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
        result["change_dir"] = f"docs/changes/{result['slug']}"
    result["on_task_branch"] = None
    result["state"] = None
    if result["slug"] and repo:
        leaf = (repo.get("branch") or "").rsplit("/", 1)[-1].lower()
        result["on_task_branch"] = leaf == result["slug"] or leaf.startswith(result["slug"] + "-")
        if repo.get("root"):
            result["state"] = task_state(repo["root"], result["change_dir"])
    if result["kind"] not in ("issue", "merge_request"):
        return result, (f"{result['system']} {result['kind']} link, not a task or an MR/PR; "
                        "open the task itself and pass its link")
    return result, None


def cmd_parse(args: argparse.Namespace) -> int:
    result, error = parse(args.url, current_repo(args.repo_dir))
    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True))
    if error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_parse = sub.add_parser("parse", help="resolve a task link against the current repo")
    p_parse.add_argument("url", help="Linear, GitLab, or GitHub task link")
    p_parse.add_argument("--repo-dir", default=".",
                         help="repository to compare the link with (default: current directory)")
    p_parse.set_defaults(fn=cmd_parse)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
