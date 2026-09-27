#!/usr/bin/env python3
"""Deterministic TDD proof: every acceptance criterion has a test, and every
test fails without the change and passes with it.

Reads the task's plan.md "## Proof" section, where each acceptance criterion
maps to the command that proves it:

    ## Proof

    - AC-1: CSV export has a header row — `pytest tests/test_export.py::test_header`
    - AC-2: the button is disabled while exporting — manual: screenshot in the MR

Checks, in order:
  1. coverage — every AC-<n> in the acceptance criteria (spec.md's
     "## Acceptance criteria", or plan.md's on the light path) appears in Proof;
  2. green — each command passes on the change;
  3. red — each command fails with the implementation removed (test files
     kept), so a test that passes without the change is caught: it does not
     test the change. Its output tail is printed; the reviewer confirms it
     failed for the expected reason.

Working-tree mode (default, during Build/Review, nothing committed yet):
implementation files are stashed for the red run and restored afterwards.
Committed mode (--base <rev>, e.g. MR/PR CI on a clean checkout):
implementation files are reset to <rev> for the red run and restored to HEAD.

Usage:
    check_tdd.py [--plan <path>] [--base <rev>] [--tests <glob>]...
                 [--timeout <seconds>] [--no-red] [--list]

Test files are recognized by name (test_*, *_test.*, *.test.*, *.spec.*) or by
a directory segment (tests, test, __tests__, spec); add patterns with --tests.
Commands come from the repo's own plan.md and run in the repo root.

Exit codes: 0 = pass, 1 = violation, 2 = usage or git error.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_plan_sync as cps  # noqa: E402

AC_RE = re.compile(r"\bAC-(\d+)\b")
PROOF_RE = re.compile(r"^\s*[-*]\s+(AC-\d+)\b(.*)$")
COMMAND_RE = re.compile(r"`([^`]+)`")
TEST_DIRS = {"tests", "test", "__tests__", "spec"}
TEST_NAMES = ("test_*", "*_test.*", "*.test.*", "*.spec.*")


def _git(repo: Path, *args: str) -> tuple[bool, str]:
    return cps._git(repo, list(args))


def is_test_path(path: str, extra: list[str]) -> bool:
    name = path.rsplit("/", 1)[-1]
    if any(fnmatch.fnmatch(name, pattern) for pattern in TEST_NAMES):
        return True
    if any(segment in TEST_DIRS for segment in path.split("/")[:-1]):
        return True
    return any(fnmatch.fnmatch(path, pattern) for pattern in extra)


def section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == f"## {heading}".lower():
            out = []
            for rest in lines[i + 1:]:
                if rest.startswith("## "):
                    break
                out.append(rest)
            return out
    return []


def parse_proof(plan_text: str) -> list[tuple[str, str | None]]:
    """[(AC id, command or None for manual evidence)]"""
    entries = []
    for line in section(plan_text, "Proof"):
        match = PROOF_RE.match(line)
        if not match:
            continue
        rest = match.group(2)
        command = COMMAND_RE.search(rest)
        if command:
            entries.append((match.group(1), command.group(1).strip()))
        elif re.search(r"\bmanual\s*:", rest, re.I):
            entries.append((match.group(1), None))
        else:
            entries.append((match.group(1), ""))
    return entries


def acceptance_ids(repo: Path, plan_path: str, plan_text: str) -> list[str]:
    spec = repo / Path(plan_path).parent / "spec.md"
    source = spec.read_text(encoding="utf-8") if spec.is_file() else plan_text
    ids = {f"AC-{n}" for line in section(source, "Acceptance criteria") for n in AC_RE.findall(line)}
    return sorted(ids, key=lambda ac: int(ac.split("-")[1]))


def run(repo: Path, command: str, timeout: int) -> tuple[int, str]:
    try:
        res = subprocess.run(command, shell=True, cwd=repo, capture_output=True,
                             text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return res.returncode, (res.stdout + res.stderr).strip()


def tail(text: str, lines: int = 6) -> str:
    return "\n".join("      " + line for line in text.splitlines()[-lines:])


def changed_worktree(repo: Path) -> list[str]:
    ok, tracked = _git(repo, "diff", "HEAD", "--name-only")
    ok2, untracked = _git(repo, "ls-files", "--others", "--exclude-standard")
    if not (ok and ok2):
        raise RuntimeError(tracked if not ok else untracked)
    return sorted({p for p in (tracked + "\n" + untracked).splitlines() if p.strip()})


def changed_since(repo: Path, base: str) -> list[str]:
    ok, out = _git(repo, "diff", "--name-only", f"{base}...HEAD")
    if not ok:
        raise RuntimeError(out)
    return [p for p in out.splitlines() if p.strip()]


def implementation_paths(changed: list[str], tests: list[str]) -> list[str]:
    return [p for p in changed if not cps._is_process_path(p, []) and not is_test_path(p, tests)]


class RedRun:
    """Remove the implementation for the red run; always restore it."""

    def __init__(self, repo: Path, paths: list[str], base: str | None):
        self.repo, self.paths, self.base = repo, paths, base

    def __enter__(self) -> "RedRun":
        if self.base is None:
            ok, out = _git(self.repo, "stash", "push", "--include-untracked",
                           "--message", "check_tdd red run", "--", *self.paths)
            if not ok:
                raise RuntimeError(f"git stash failed: {out}")
        else:
            for path in self.paths:
                exists, _ = _git(self.repo, "cat-file", "-e", f"{self.base}:{path}")
                if exists:
                    ok, out = _git(self.repo, "checkout", self.base, "--", path)
                    if not ok:
                        raise RuntimeError(out)
                else:
                    (self.repo / path).unlink(missing_ok=True)
        return self

    def __exit__(self, *exc: object) -> None:
        if self.base is None:
            ok, out = _git(self.repo, "stash", "pop")
            if not ok:
                print("error: could not restore the implementation after the red run:\n"
                      f"  {out}\n  it is in `git stash list` as 'check_tdd red run'; "
                      "restore it with `git stash pop` before anything else", file=sys.stderr)
                raise SystemExit(2)
        else:
            for path in self.paths:
                at_head, _ = _git(self.repo, "cat-file", "-e", f"HEAD:{path}")
                if at_head:
                    _git(self.repo, "checkout", "HEAD", "--", path)
                else:
                    _git(self.repo, "rm", "-q", "--cached", "--ignore-unmatch", "--", path)
                    (self.repo / path).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plan", default=None, help="plan path (default: the task's docs/changes/*/plan.md)")
    parser.add_argument("--base", default=None, help="committed mode: compare HEAD with this revision")
    parser.add_argument("--tests", action="append", default=[], help="extra test-file glob")
    parser.add_argument("--timeout", type=int, default=600, help="seconds per command (default 600)")
    parser.add_argument("--no-red", action="store_true", help="skip the red run (coverage and green only)")
    parser.add_argument("--list", action="store_true", help="print the AC → proof map and exit")
    args = parser.parse_args(argv)

    repo = Path.cwd()
    if args.base:
        ok, status = _git(repo, "status", "--porcelain")
        if not ok or status.strip():
            print("error: --base needs a clean working tree (commit or stash first)", file=sys.stderr)
            return 2
    try:
        changed = changed_since(repo, args.base) if args.base else changed_worktree(repo)
    except RuntimeError as exc:
        print(f"error: git failed: {exc}", file=sys.stderr)
        return 2
    plan_path, error = cps._resolve_plan(repo, changed, args.plan, use_branch=True)
    if error or plan_path is None:
        print(f"error: {error or 'no plan found; pass --plan docs/changes/<task>/plan.md'}", file=sys.stderr)
        return 2
    plan_file = repo / plan_path
    if not plan_file.is_file():
        print(f"error: {plan_path} not found", file=sys.stderr)
        return 2
    plan_text = plan_file.read_text(encoding="utf-8")

    proof = parse_proof(plan_text)
    criteria = acceptance_ids(repo, plan_path, plan_text)
    if args.list:
        for ac, command in proof:
            print(f"{ac}: {command if command is not None else 'manual'}")
        return 0

    failures = 0
    mapped = {ac for ac, _ in proof}
    if not criteria:
        print('error: no acceptance criteria (AC-<n>) under "## Acceptance criteria"', file=sys.stderr)
        return 1
    for ac in criteria:
        if ac not in mapped:
            print(f"FAIL coverage: {ac} has no entry under ## Proof in {plan_path}")
            failures += 1
    for ac, command in proof:
        if command == "":
            print(f"FAIL coverage: {ac} names neither a `command` nor manual: evidence")
            failures += 1

    automated = [(ac, cmd) for ac, cmd in proof if cmd]
    for ac, command in automated:
        code, output = run(repo, command, args.timeout)
        if code == 0:
            print(f"ok   green: {ac} — {command}")
        else:
            print(f"FAIL green: {ac} fails with the change — {command}\n{tail(output)}")
            failures += 1

    if automated and not args.no_red:
        impl = implementation_paths(changed, args.tests)
        if not impl:
            print("FAIL red: no implementation files changed, so no test can prove the change")
            failures += 1
        else:
            try:
                with RedRun(repo, impl, args.base):
                    for ac, command in automated:
                        code, output = run(repo, command, args.timeout)
                        if code != 0:
                            print(f"ok   red:   {ac} fails without the change — confirm the reason:\n{tail(output, 3)}")
                        else:
                            print(f"FAIL red:   {ac} passes without the change, so it does not test it — {command}")
                            failures += 1
            except RuntimeError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2

    manual = [ac for ac, cmd in proof if cmd is None]
    if manual:
        print(f"note manual evidence expected in the MR/PR for: {', '.join(manual)}")
    print(f"check_tdd: {len(criteria)} criteria, {len(automated)} automated, "
          f"{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
