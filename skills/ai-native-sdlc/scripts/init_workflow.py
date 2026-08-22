#!/usr/bin/env python3
"""Scaffold the AI-native SDLC artifact skeleton in a project directory.

Usage:
    python3 init_workflow.py <project-dir> [--name "<project name>"] [--force]

Creates:
    intent/intent.md          intent template (copy of assets/intent.md)
    CLAUDE.md                 repository-memory starter
    REVIEW.md                 review standards
    hooks/production-gate.sh  release authorization hook (executable)
    bands.yaml                monitoring control bands
    evals/example.md          eval case example

Existing files are skipped unless --force is passed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"

FILES = {
    "intent/intent.md": "intent.md",
    "CLAUDE.md": "CLAUDE.md",
    "REVIEW.md": "REVIEW.md",
    "hooks/production-gate.sh": "production-gate.sh",
    "bands.yaml": "bands.yaml",
    "evals/example.md": "evals.example.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="target project directory (default: current directory)",
    )
    parser.add_argument(
        "--name",
        help="project/product name to fill into the intent title",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing files",
    )
    args = parser.parse_args()

    if not ASSET_DIR.is_dir():
        print(f"error: assets directory not found at {ASSET_DIR}", file=sys.stderr)
        return 1

    root = Path(args.project_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    skipped: list[str] = []
    for rel_dest, asset_name in FILES.items():
        src = ASSET_DIR / asset_name
        dest = root / rel_dest
        if not src.is_file():
            print(f"error: missing asset {src}", file=sys.stderr)
            return 1
        if dest.exists() and not args.force:
            skipped.append(str(dest.relative_to(root)))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        if args.name:
            text = text.replace("<Title>", args.name)
        dest.write_text(text, encoding="utf-8")
        if dest.name == "production-gate.sh":
            dest.chmod(dest.stat().st_mode | 0o111)
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
    print()
    print("Next steps:")
    print("  1. Open intent/intent.md and describe the goal in your own words.")
    print("  2. Tell your agent: run the AI-native SDLC workflow from this intent.")
    print("  3. Commit the skeleton: git init && git add -A && git commit -m 'scaffold ai-native-sdlc workflow'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
