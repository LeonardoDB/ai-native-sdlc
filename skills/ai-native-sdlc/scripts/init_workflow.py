#!/usr/bin/env python3
"""Scaffold the AI-native SDLC skeleton in a project directory.

Usage:
    python3 init_workflow.py <project-dir> [--dry-run] [--force] [--git]

Creates:
    CLAUDE.md                   repository-memory starter
    REVIEW.md                   review standards
    scripts/check_plan_sync.py  deterministic plan-sync check (pre-commit / MR/PR CI)
    scripts/check_tdd.py        deterministic TDD proof (AC coverage, green/red)
    scripts/check_diff_hygiene.py  suppressions, skipped tests, rewritten tests
    scripts/check_mutations.py  mutation check on the changed lines
    scripts/impact_map.py       dependents, callers, and risk of the files a change touches
    .gitignore                  basic ignore rules

No intent.md: the intent lives in the tracker (Linear, GitLab, GitHub); a
task on the board is an accepted intent (references/trackers.md). Each task's
spec.md and plan.md are written by the workflow into docs/changes/<task>/.
The loop ends at the opened MR/PR, so nothing for deploy or monitoring.

Existing files are skipped unless --force is passed. --dry-run prints the
plan without writing anything (not even the project directory).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# dest -> skill-relative source (assets/ for templates, scripts/ for tooling)
FILES = {
    "CLAUDE.md": "assets/CLAUDE.md",
    "REVIEW.md": "assets/REVIEW.md",
    "scripts/check_plan_sync.py": "scripts/check_plan_sync.py",
    "scripts/check_tdd.py": "scripts/check_tdd.py",
    "scripts/check_diff_hygiene.py": "scripts/check_diff_hygiene.py",
    "scripts/check_mutations.py": "scripts/check_mutations.py",
    "scripts/impact_map.py": "scripts/impact_map.py",
    ".gitignore": "assets/.gitignore",
}


def _git_init_and_commit(root: Path) -> None:
    if (root / ".git").exists():
        print("  git: already a repository; skipping init")
        return
    try:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "scaffold ai-native-sdlc workflow"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        print("  git: initialized and created the initial commit")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  git: skipped (git unavailable or commit failed); run git init manually")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="target project directory (default: current directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan without writing anything",
    )
    parser.add_argument(
        "--git",
        action="store_true",
        help="git init and commit the skeleton (requires git)",
    )
    args = parser.parse_args()

    if not SKILL_DIR.is_dir():
        print(f"error: skill directory not found at {SKILL_DIR}", file=sys.stderr)
        return 1

    root = Path(args.project_dir).expanduser().resolve()

    plan: list[tuple[Path, str, str]] = []  # (dest, src, mode)
    for rel_dest, rel_src in FILES.items():
        src = SKILL_DIR / rel_src
        if not src.is_file():
            print(f"error: missing source {src}", file=sys.stderr)
            return 1
        dest = root / rel_dest
        mode = "write" if args.force or not dest.exists() else "skip"
        plan.append((dest, rel_src, mode))

    if args.dry_run:
        print(f"Dry run: would scaffold AI-native SDLC skeleton in {root}")
        for dest, rel_src, mode in plan:
            print(f"  [{mode}] {dest.relative_to(root)}  <- {rel_src}")
        return 0

    root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    skipped: list[str] = []
    for dest, rel_src, mode in plan:
        if mode == "skip":
            skipped.append(str(dest.relative_to(root)))
            continue
        text = (SKILL_DIR / rel_src).read_text(encoding="utf-8")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        written.append(str(dest.relative_to(root)))

    print(f"Scaffolded AI-native SDLC skeleton in {root}")
    if written:
        print("  created:")
        for name in written:
            print(f"    - {name}")
    if skipped:
        print("  skipped (already exist; use --force to overwrite):")
        for name in skipped:
            print(f"    - {name}")

    if args.git:
        _git_init_and_commit(root)

    print()
    print("Next steps:")
    print("  1. Fill in CLAUDE.md (commands, conventions, optional Tracker /")
    print("     Knowledge base / Commit and MR/PR sections).")
    print("  2. Tell your agent: run the AI-native SDLC workflow for <task link>.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
