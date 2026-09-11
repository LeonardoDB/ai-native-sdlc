#!/usr/bin/env python3
"""Form/email demand intake for the agent org (F3).

Normalizes form and email submissions into the same versioned markdown record
format GitHub intake already produces under org/intake/, so the product
engineering agent has one queue regardless of channel. Network-free and
deterministic.

Usage:
    intake.py add --source form|email --record-id <id> \\
        [--author <who>] [--priority low|normal|high] \\
        [--received-at <ISO-8601>] \\
        [--summary <text> | --summary-file <path>] \\
        [--details <text> | --details-file <path>] \\
        [--output org/intake/<source>/] [--dry-run]
    intake.py list [--source form|email] [--status new|triaged|ticket_filed|
                   intent_drafted|done]

Exit codes: 0 = ok, 1 = validation/runtime failure, 2 = usage error.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
INTAKE_ROOT = PROJECT_ROOT / "org" / "intake"
RECORD_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
VALID_STATUSES = ("new", "triaged", "ticket_filed", "intent_drafted", "done")
SOURCE_DIRS = {"form": "forms", "email": "email"}


def _now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_iso(value: str) -> str:
    try:
        parsed = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"cannot parse received_at timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def _read_text(path: str | None, kind: str) -> str | None:
    if path is None:
        return None
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"{kind} file not found: {p}")
    return p.read_text(encoding="utf-8")


def _existing_record_ids() -> dict[str, Path]:
    found: dict[str, Path] = {}
    if not INTAKE_ROOT.is_dir():
        return found
    for record in INTAKE_ROOT.rglob("*.md"):
        text = record.read_text(encoding="utf-8")
        match = re.search(r"(?m)^record_id\s*:\s*(.+)$", text)
        if match:
            found[match.group(1).strip()] = record
    return found


def _record_text(
    source: str,
    record_id: str,
    received_at: str,
    author: str,
    priority: str,
    summary: str,
    details: str | None,
) -> str:
    detail_body = details.strip() if details and details.strip() else "(none)"
    return (
        "---\n"
        f"source: {source}\n"
        f"record_id: {record_id}\n"
        f"received_at: {received_at}\n"
        f"author: {author}\n"
        f"priority: {priority}\n"
        "---\n\n"
        "## Summary\n\n"
        f"{summary.strip()}\n\n"
        "## Details\n\n"
        f"{detail_body}\n\n"
        "## Status\n\n"
        "new\n"
    )


def cmd_add(args: argparse.Namespace) -> int:
    if not RECORD_ID_RE.match(args.record_id):
        print(
            "error: record_id must match [A-Za-z0-9._-]+ "
            "(no slashes, spaces, or path separators)",
            file=sys.stderr,
        )
        return 1

    try:
        received_at = _canonical_iso(args.received_at)
        summary = args.summary if args.summary is not None else _read_text(
            args.summary_file, "summary"
        )
        details = args.details if args.details is not None else _read_text(
            args.details_file, "details"
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not summary or not summary.strip():
        print("error: a summary is required (--summary or --summary-file)", file=sys.stderr)
        return 1

    default_dir = INTAKE_ROOT / SOURCE_DIRS[args.source]
    output_dir = _resolve(PROJECT_ROOT, args.output) if args.output else default_dir
    try:
        resolved_output = output_dir.resolve()
        intake_root = INTAKE_ROOT.resolve()
        if intake_root not in resolved_output.parents and resolved_output != intake_root:
            print(
                f"error: output path {resolved_output} is outside the intake directory",
                file=sys.stderr,
            )
            return 1
    except OSError as exc:
        print(f"error: cannot resolve output path: {exc}", file=sys.stderr)
        return 1

    existing = _existing_record_ids()
    if args.record_id in existing:
        print(
            f"error: record_id {args.record_id!r} already exists at {existing[args.record_id]}",
            file=sys.stderr,
        )
        return 1

    record_path = resolved_output / f"{args.record_id}.md"
    text = _record_text(
        args.source,
        args.record_id,
        received_at,
        args.author,
        args.priority,
        summary,
        details,
    )
    if args.dry_run:
        print(f"dry run: would write {record_path}")
        return 0
    try:
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text(text, encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write {record_path}: {exc}", file=sys.stderr)
        return 1
    print(f"recorded {args.record_id} -> {record_path}")
    return 0


def _frontmatter(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if not text.startswith("---"):
        return out
    rest = text.split("\n", 1)[1] if "\n" in text else ""
    if "---" not in rest:
        return out
    block = rest.split("---", 1)[0]
    for line in block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def _queue_files() -> list[Path]:
    if not INTAKE_ROOT.is_dir():
        return []
    return sorted(INTAKE_ROOT.rglob("*.md"))


def _record_status(text: str) -> str:
    """Read the status only from the record's '## Status' section."""
    in_status = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower() == "## status":
            in_status = True
            continue
        if in_status:
            if stripped.startswith("## "):
                break
            if stripped in VALID_STATUSES:
                return stripped
    return "unknown"


def cmd_list(args: argparse.Namespace) -> int:
    records = []
    for path in _queue_files():
        text = path.read_text(encoding="utf-8")
        meta = _frontmatter(text)
        if args.source and meta.get("source") != args.source:
            continue
        status = _record_status(text)
        if args.status and status != args.status:
            continue
        records.append((path, meta, status))
    for path, meta, status in records:
        print(
            f"{meta.get('source', '?'):6} {meta.get('record_id', path.stem):24} "
            f"{meta.get('priority', 'normal'):7} {status:14} {meta.get('author', '')}"
        )
    print(f"{len(records)} record(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="ingest a form/email record")
    add.add_argument("--source", choices=["form", "email"], required=True)
    add.add_argument("--record-id", required=True)
    add.add_argument("--author", default="unknown")
    add.add_argument("--priority", choices=["low", "normal", "high"], default="normal")
    add.add_argument("--received-at", default=None, help="ISO-8601 UTC (default: now)")
    summary_group = add.add_mutually_exclusive_group()
    summary_group.add_argument("--summary", default=None)
    summary_group.add_argument("--summary-file", default=None)
    detail_group = add.add_mutually_exclusive_group()
    detail_group.add_argument("--details", default=None)
    detail_group.add_argument("--details-file", default=None)
    add.add_argument("--output", default=None)
    add.add_argument("--dry-run", action="store_true")
    add.set_defaults(fn=cmd_add)

    listing = sub.add_parser("list", help="list the intake queue")
    listing.add_argument("--source", choices=["form", "email"])
    listing.add_argument("--status", choices=list(VALID_STATUSES))
    listing.set_defaults(fn=cmd_list)

    args = parser.parse_args(argv)
    if args.command == "add" and args.received_at is None:
        args.received_at = _now_utc()
    if args.command == "add" and args.summary is None and args.summary_file is None:
        parser.error("--summary or --summary-file is required")
    try:
        return args.fn(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
