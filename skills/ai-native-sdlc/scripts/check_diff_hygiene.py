#!/usr/bin/env python3
"""Deterministic diff hygiene: no silent escape hatches, no silently weakened tests.

Three checks — two on the lines a change adds or removes, one on the plan:

  1. escape hatches — an added line that suppresses the type checker or the
     linter (`any`, `as any`, `@ts-ignore`, `# type: ignore`, `eslint-disable`,
     `# noqa`, ...) or skips/focuses a test (`.skip(`, `.only(`, `xit(`,
     `@pytest.mark.skip`, `@Disabled`, ...) fails unless the same line says
     why, with `reason:` (e.g. `// @ts-expect-error reason: upstream types
     wrong, see #123`).
  2. test changes — a pre-existing test file whose lines are removed or
     rewritten (not just added to) must be listed under the plan's
     "## Test changes" with the reason. Fix the code, not the test; when the
     test itself is wrong, say so there.
  3. learnings triaged — every `- [ ]` entry under the plan's "## Learnings"
     is promoted to a knowledge store or dropped before delivery
     (references/knowledge.md).

Working-tree mode (default): the change is the working tree (untracked files
included) against HEAD. Committed mode (--base <rev>): base...HEAD.

Usage:
    check_diff_hygiene.py [--base <rev>] [--plan <path>] [--tests <glob>]...

Markdown and process files (docs/, CLAUDE.md, ...) are not scanned.
Exit codes: 0 = pass, 1 = violation, 2 = usage or git error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_plan_sync as cps  # noqa: E402
import check_tdd as tdd  # noqa: E402

ESCAPE_HATCHES = [
    ("type suppression", re.compile(
        r"@ts-(?:ignore|expect-error|nocheck)|#\s*type:\s*ignore|#\s*pyright:\s*ignore"
        r"|#\s*mypy:\s*ignore|:\s*any\b|\bas\s+any\b|<any>|\bcast\(\s*Any\b")),
    ("lint suppression", re.compile(
        r"eslint-disable|#\s*noqa\b|#\s*pylint:\s*disable|//\s*nolint|@SuppressWarnings"
        r"|#\[allow\(|@Suppress\(|rubocop:disable|biome-ignore")),
    ("skipped or focused test", re.compile(
        r"\b(?:it|test|describe|context)\.(?:skip|only|todo)\(|\b(?:xit|xdescribe|fit|fdescribe)\("
        r"|@pytest\.mark\.(?:skip|xfail)|@unittest\.skip|\bpytest\.skip\(|@Disabled\b|@Ignore\b"
        r"|\bt\.Skip\(|#\[ignore\]")),
]
REASON_RE = re.compile(r"\breason\s*:", re.I)
UNTRIAGED_RE = re.compile(r"^\s*[-*]\s+\[ \]\s+\S")
HUNK_FILE_RE = re.compile(r"^\+\+\+ b/(.+)$")


def _git(repo: Path, *args: str) -> tuple[bool, str]:
    return cps._git(repo, list(args))


def scanned(path: str) -> bool:
    return not path.endswith((".md", ".markdown", ".txt")) and not cps._is_process_path(path, [])


def diff_lines(repo: Path, base: str | None) -> tuple[dict[str, list[str]], dict[str, int]]:
    """({path: added lines}, {path: removed-line count}) for the change."""
    args = ["diff", "--unified=0", "--no-color"]
    args += [f"{base}...HEAD"] if base else ["HEAD"]
    ok, out = _git(repo, *args)
    if not ok:
        raise RuntimeError(out)
    added: dict[str, list[str]] = {}
    removed: dict[str, int] = {}
    current = old = None
    for line in out.splitlines():
        if line.startswith("--- "):
            old = line[6:] if line.startswith("--- a/") else None
            continue
        if line.startswith("+++ "):
            match = HUNK_FILE_RE.match(line)
            current = match.group(1) if match else old  # "+++ /dev/null": a deleted file
            continue
        if current and line.startswith("+"):
            added.setdefault(current, []).append(line[1:])
        elif current and line.startswith("-"):
            removed[current] = removed.get(current, 0) + 1
    if base is None:
        ok, untracked = _git(repo, "ls-files", "--others", "--exclude-standard")
        for path in untracked.splitlines() if ok else []:
            try:
                added[path] = (repo / path).read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
    return added, removed


def listed_test_changes(plan_text: str) -> str:
    return "\n".join(tdd.section(plan_text, "Test changes"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default=None, help="committed mode: compare HEAD with this revision")
    parser.add_argument("--plan", default=None, help="plan path (default: the task's docs/changes/*/plan.md)")
    parser.add_argument("--tests", action="append", default=[], help="extra test-file glob")
    args = parser.parse_args(argv)

    repo = Path.cwd()
    try:
        added, removed = diff_lines(repo, args.base)
    except RuntimeError as exc:
        print(f"error: git diff failed: {exc}", file=sys.stderr)
        return 2

    failures = 0
    for path in sorted(added):
        if not scanned(path):
            continue
        for number, line in enumerate(added[path], 1):
            for label, pattern in ESCAPE_HATCHES:
                if pattern.search(line) and not REASON_RE.search(line):
                    print(f"FAIL {label} without `reason:` in {path}: {line.strip()[:120]}")
                    failures += 1

    changed = sorted(set(added) | set(removed))
    plan_path, _ = cps._resolve_plan(repo, changed, args.plan, use_branch=True)
    plan_file = repo / plan_path if plan_path else None
    plan_text = plan_file.read_text(encoding="utf-8") if plan_file and plan_file.is_file() else ""

    for line in tdd.section(plan_text, "Learnings"):
        if UNTRIAGED_RE.match(line):
            print(f"FAIL learning not triaged in {plan_path}: {line.strip()[:100]} "
                  "(promote it to a store or drop it)")
            failures += 1

    weakened = sorted(p for p, count in removed.items()
                      if count and scanned(p) and tdd.is_test_path(p, args.tests))
    if weakened:
        listed = listed_test_changes(plan_text)
        for path in weakened:
            if path not in listed:
                print(f"FAIL existing test changed, not listed under ## Test changes: {path} "
                      f"({removed[path]} line(s) removed or rewritten)")
                failures += 1

    print(f"check_diff_hygiene: {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
