#!/usr/bin/env python3
"""Deterministic plan-sync enforcement.

Backs the "Plan mode first" hard rule: implementation changes cannot pass an
MR/PR or pre-commit check without an approved plan whose "Files that change"
manifest covers the files, and departures from the plan must be declared in
the plan in the same change set.

Each task keeps its artifacts in its own folder, docs/changes/<task>/ (spec.md
and plan.md), so parallel branches in one repo never touch the same files.
The plan for a change is the docs/changes/*/plan.md the diff touches; pass
--plan when the diff touches several.

Usage:
    check_plan_sync.py --base <rev> --head <rev> [--plan <path>]
                       [--ignore <glob>]... [--two-dot]
    check_plan_sync.py --hook [--plan <path>] [--ignore <glob>]...

MR/PR mode defaults to a three-dot diff (merge-base). Hook mode validates the
staged diff (HEAD vs index) and reads the plan from the index; when the plan
is not staged (it went in an earlier commit), the task folder named by the
current branch is used (branch fix/42-date-bug -> docs/changes/42/plan.md).

Exit codes: 0 = pass, 1 = violation, 2 = usage error.
"""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

CHANGES_DIR = "docs/changes"

# Paths that are process artifacts, not implementation. The checker never
# requires a plan for these; adopters may add more via --ignore.
PROCESS_ENTRIES = (
    "docs/",
    "REVIEW.md",
    "CLAUDE.md",
    "AGENTS.md",
    ".github/",
    ".gitlab/",
    "CHANGELOG.md",
    "README.md",
    "LICENSE",
    "SECURITY.md",
)

STATUS_RE = re.compile(r"(?im)^\s*[-*]\s*Status\s*:\s*Approved\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$")


def _git(repo: Path, args: list[str]) -> tuple[bool, str]:
    try:
        res = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return False, str(exc)
    if res.returncode != 0:
        return False, (res.stderr or res.stdout).strip()
    return True, res.stdout


def _is_process_path(path: str, ignores: list[str]) -> bool:
    if any(fnmatch.fnmatch(path, pattern) for pattern in ignores):
        return True
    normalized = path[2:] if path.startswith("./") else path
    for entry in PROCESS_ENTRIES:
        if entry.endswith("/"):
            if normalized == entry.rstrip("/") or normalized.startswith(entry):
                return True
        elif normalized == entry:
            return True
    return False


def _changed_files_pr(repo: Path, base: str, head: str, two_dot: bool) -> tuple[bool, list[str] | str]:
    sep = ".." if two_dot else "..."
    ok, out = _git(repo, ["diff", "--name-only", f"{base}{sep}{head}"])
    if not ok:
        return False, out
    return True, [line for line in out.splitlines() if line.strip()]


def _changed_files_hook(repo: Path) -> tuple[bool, list[str] | str]:
    ok, out = _git(repo, ["diff", "--cached", "--name-only"])
    if not ok:
        return False, out
    return True, [line for line in out.splitlines() if line.strip()]


def _show(repo: Path, rev: str, path: str) -> tuple[bool, str]:
    return _git(repo, ["show", f"{rev}:{path}"])


def _plan_candidates(changed: list[str]) -> list[str]:
    return sorted(
        path for path in changed
        if path.startswith(CHANGES_DIR + "/") and path.endswith("/plan.md")
        and path.count("/") == CHANGES_DIR.count("/") + 2
    )


def _manifest_entries(text: str) -> list[str]:
    """Parse the bullet list under '## Files that change'."""
    lines = text.splitlines()
    start = -1
    for i, line in enumerate(lines):
        if line.strip().lower() == "## files that change":
            start = i
            break
    if start == -1:
        raise ValueError('plan.md has no "Files that change" section')

    section: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        section.append(line)

    bullets = [line for line in section if BULLET_RE.match(line)]
    if not bullets:
        raise ValueError(
            'plan.md "Files that change" must be a bullet list of paths/globs'
        )

    entries: list[str] = []
    for line in bullets:
        match = BULLET_RE.match(line)
        assert match is not None
        entry = _normalize_entry(match.group(1))
        if entry and entry != "-":
            entries.append(entry)
    return entries


def _normalize_entry(entry: str) -> str:
    entry = entry.strip()
    if entry.startswith("`") and entry.endswith("`") and len(entry) > 1:
        entry = entry[1:-1]
    else:
        entry = entry.replace("`", "")
    entry = re.sub(r"\s+\((?:new|modified|deleted|renamed|added)\)\s*$", "", entry, flags=re.I)
    entry = re.sub(r"\s+(?:new|modified|deleted|renamed|added)\s*$", "", entry, flags=re.I)
    return entry.strip()


def _plan_is_approved(text: str) -> bool:
    return bool(STATUS_RE.search(text))


def _added_manifest_entries(old_text: str | None, new_text: str) -> list[str]:
    old_lines = (old_text or "").splitlines()
    new_lines = new_text.splitlines()
    try:
        old_entries = _manifest_entries("\n".join(old_lines)) if old_text is not None else []
    except ValueError:
        # Legacy plans may still be prose; migrating them to the bullet
        # manifest in the same change is supported. The head manifest is
        # authoritative, so treat the old manifest as empty.
        old_entries = []
    added: list[str] = []
    if old_entries:
        diff = difflib.unified_diff(old_lines, new_lines, lineterm="", n=0)
        for line in diff:
            if not line.startswith("+"):
                continue
            stripped = line[1:].strip()
            match = BULLET_RE.match(stripped)
            if not match:
                continue
            added.append(_normalize_entry(match.group(1)))
    else:
        added = _manifest_entries(new_text)
    return added


def _branch_plan(repo: Path) -> str | None:
    """The plan whose task folder names the current branch (fix/42-x -> docs/changes/42)."""
    ok, branch = _git(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    if not ok:
        return None
    leaf = branch.strip().rsplit("/", 1)[-1].lower()
    root = repo / CHANGES_DIR
    if not leaf or not root.is_dir():
        return None
    matches = [
        d.name for d in root.iterdir()
        if d.is_dir() and (d / "plan.md").is_file()
        and (leaf == d.name.lower() or leaf.startswith(d.name.lower() + "-"))
    ]
    # Prefer the longest folder name: "42" and "42-1" cannot both win.
    return f"{CHANGES_DIR}/{max(matches, key=len)}/plan.md" if matches else None


def _resolve_plan(
    repo: Path, changed: list[str], explicit: str | None, use_branch: bool
) -> tuple[str | None, str | None]:
    """Return (plan path, error)."""
    if explicit:
        return explicit, None
    candidates = _plan_candidates(changed)
    if len(candidates) > 1:
        return None, f"several plans changed ({', '.join(candidates)}); pass --plan"
    if candidates:
        return candidates[0], None
    return (_branch_plan(repo) if use_branch else None), None


def _check(
    repo: Path,
    changed: list[str],
    plan_path: str | None,
    plan_text: str | None,
    plan_diff_base: str | None,
    ignores: list[str],
) -> int:
    implementation = [
        path for path in changed if not _is_process_path(path, ignores)
    ]
    if not implementation:
        return 0

    if plan_path is None or plan_text is None:
        print(
            f"error: no plan: add {CHANGES_DIR}/<task>/plan.md to this change "
            "(or pass --plan)",
            file=sys.stderr,
        )
        return 1
    if not _plan_is_approved(plan_text):
        print(f"error: {plan_path} not Approved", file=sys.stderr)
        return 1

    try:
        entries = _manifest_entries(plan_text)
    except ValueError as exc:
        print(f"error: {plan_path}: {exc}", file=sys.stderr)
        return 1

    old_text = None
    if plan_diff_base is not None:
        old_ok, old_text = _show(repo, plan_diff_base, plan_path)
        if not old_ok:
            old_text = None
    added = _added_manifest_entries(old_text, plan_text) if old_text is not None else []

    unplanned: list[str] = []
    for path in implementation:
        if any(fnmatch.fnmatch(path, entry) for entry in entries):
            continue
        if any(fnmatch.fnmatch(path, entry) for entry in added):
            continue
        unplanned.append(path)

    if unplanned:
        details = " ".join(
            f'{path} (add a matching entry under "Files that change" in {plan_path})'
            for path in sorted(unplanned)
        )
        print(f"error: unplanned files: {details}", file=sys.stderr)
        return 1
    return 0


def _read_plan(repo: Path, rev: str, plan_path: str | None) -> str | None:
    if plan_path is None:
        return None
    ok, text = _show(repo, rev, plan_path)
    return text if ok and text.strip() else None


def cmd_pr(args: argparse.Namespace, repo: Path) -> int:
    ok, changed = _changed_files_pr(repo, args.base, args.head, args.two_dot)
    if not ok:
        print(f"error: git diff failed: {changed}", file=sys.stderr)
        return 1
    plan_path, error = _resolve_plan(repo, changed, args.plan, use_branch=False)
    if error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    plan_text = _read_plan(repo, args.head, plan_path)
    return _check(repo, changed, plan_path, plan_text, args.base, args.ignore)


def cmd_hook(args: argparse.Namespace, repo: Path) -> int:
    ok, changed = _changed_files_hook(repo)
    if not ok:
        print(f"error: git diff failed: {changed}", file=sys.stderr)
        return 1
    plan_path, error = _resolve_plan(repo, changed, args.plan, use_branch=True)
    if error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    plan_text = _read_plan(repo, "", plan_path)  # "" = the index
    return _check(repo, changed, plan_path, plan_text, "HEAD", args.ignore)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", action="store_true", help="check the staged diff")
    parser.add_argument("--base", default=None, help="base revision (PR mode)")
    parser.add_argument("--head", default=None, help="head revision (PR mode)")
    parser.add_argument("--plan", default=None,
                        help=f"plan path (default: the {CHANGES_DIR}/*/plan.md the diff touches)")
    parser.add_argument("--ignore", action="append", default=[], help="additional process-path glob")
    parser.add_argument(
        "--two-dot",
        action="store_true",
        help="use literal base..head instead of merge-base base...head",
    )
    args = parser.parse_args(argv)

    if args.hook and (args.base or args.head):
        parser.error("--hook cannot be combined with --base/--head")
    if not args.hook and not (args.base and args.head):
        parser.error("pass --hook or both --base and --head")

    repo = Path.cwd()
    if args.hook:
        return cmd_hook(args, repo)
    return cmd_pr(args, repo)


if __name__ == "__main__":
    raise SystemExit(main())
