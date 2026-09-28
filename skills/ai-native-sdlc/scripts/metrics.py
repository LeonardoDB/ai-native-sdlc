#!/usr/bin/env python3
"""Rework and quality metrics per task, from what the workflow already records.

Every task leaves docs/changes/<task>/ (spec.md on the full path, plan.md
always) in git. This reads those folders — in one repo or many — and reports,
per task and in aggregate:

    path            light or full
    criteria        acceptance criteria, and how many rely on manual evidence
    spec_rework     commits to spec.md after plan.md first appeared
                    (requirements that changed once building started)
    plan_edits      commits to plan.md after its first
    review_rounds   "### Round <n>" headings under plan.md's ## Review
    deviations      bullets under ## Deviations
    test_changes    existing tests edited, from ## Test changes
    survivors       accepted surviving mutants, from ## Surviving mutants
    promoted        learnings promoted to a knowledge store, from ## Learnings
    dropped         learnings dropped at triage
    lead_days       first to last commit touching the task folder

With --forge it also asks the forge (`gh` or `glab`, from the repo's origin)
for the MR/PR whose source branch carries the task slug: its human comment
count and the days from opening to merge.

Usage:
    metrics.py [--repos <path>...] [--forge] [--json]

Exit codes: 0 = ok, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_tdd as tdd  # noqa: E402
import tracker_link as tl  # noqa: E402

BULLET_RE = re.compile(r"^\s*[-*]\s+\S")
ROUND_RE = re.compile(r"^###\s+Round\b", re.I)


def git(repo: Path, *args: str) -> list[str]:
    try:
        res = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    return [l for l in res.stdout.splitlines() if l.strip()] if res.returncode == 0 else []


def commit_times(repo: Path, path: str) -> list[int]:
    """Commit timestamps touching path, oldest first."""
    return sorted(int(t) for t in git(repo, "log", "--format=%ct", "--", path))


def bullets(text: str, heading: str) -> int:
    return sum(1 for line in tdd.section(text, heading)
               if BULLET_RE.match(line) and not line.strip().startswith("- <"))


def task_metrics(repo: Path, folder: Path) -> dict:
    rel = folder.relative_to(repo).as_posix()
    spec, plan = folder / "spec.md", folder / "plan.md"
    plan_text = plan.read_text(encoding="utf-8") if plan.is_file() else ""
    spec_text = spec.read_text(encoding="utf-8") if spec.is_file() else ""
    criteria = sorted(set(re.findall(r"\bAC-\d+\b", "\n".join(
        tdd.section(spec_text or plan_text, "Acceptance criteria")))))
    proof = tdd.parse_proof(plan_text)
    plan_times = commit_times(repo, f"{rel}/plan.md")
    spec_times = commit_times(repo, f"{rel}/spec.md")
    folder_times = commit_times(repo, rel)
    first_plan = plan_times[0] if plan_times else None
    return {
        "repo": repo.name,
        "task": folder.name,
        "path": "full" if spec.is_file() else "light",
        "criteria": len(criteria),
        "manual_criteria": sum(1 for _, cmd in proof if cmd is None),
        "spec_rework": sum(1 for t in spec_times if first_plan is not None and t > first_plan),
        "plan_edits": max(0, len(plan_times) - 1),
        "review_rounds": sum(1 for line in tdd.section(plan_text, "Review") if ROUND_RE.match(line)),
        "deviations": bullets(plan_text, "Deviations"),
        "test_changes": bullets(plan_text, "Test changes"),
        "survivors": bullets(plan_text, "Surviving mutants"),
        "promoted": sum(1 for l in tdd.section(plan_text, "Learnings") if re.match(r"^\s*[-*]\s+\[promoted", l)),
        "dropped": sum(1 for l in tdd.section(plan_text, "Learnings") if re.match(r"^\s*[-*]\s+\[dropped", l)),
        "lead_days": round((folder_times[-1] - folder_times[0]) / 86400, 1) if folder_times else None,
    }


def _days(start: str | None, end: str | None) -> float | None:
    if not start or not end:
        return None
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return round((parse(end) - parse(start)).total_seconds() / 86400, 1)


def forge_metrics(repo: Path, slug: str) -> dict:
    remote = tl.current_repo(str(repo))
    forge = remote.get("forge") if remote else None
    try:
        if forge == "github":
            res = subprocess.run(["gh", "pr", "list", "--state", "all", "--search", f"head:{slug}",
                                  "--json", "number,headRefName,createdAt,mergedAt,comments"],
                                 cwd=repo, capture_output=True, text=True, timeout=60)
            items = json.loads(res.stdout or "[]") if res.returncode == 0 else []
            items = [i for i in items if re.search(rf"(^|/){re.escape(slug)}(-|$)", i.get("headRefName", ""))]
            if items:
                pr = items[0]
                return {"mr": f"#{pr.get('number')}", "mr_comments": len(pr.get("comments") or []),
                        "mr_days": _days(pr.get("createdAt"), pr.get("mergedAt"))}
        elif forge == "gitlab":
            res = subprocess.run(["glab", "mr", "list", "--all", "--search", slug, "-F", "json"],
                                 cwd=repo, capture_output=True, text=True, timeout=60)
            items = json.loads(res.stdout or "[]") if res.returncode == 0 else []
            items = [i for i in items if re.search(rf"(^|/){re.escape(slug)}(-|$)", i.get("source_branch", ""))]
            if items:
                mr = items[0]
                return {"mr": f"!{mr.get('iid')}", "mr_comments": mr.get("user_notes_count"),
                        "mr_days": _days(mr.get("created_at"), mr.get("merged_at"))}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return {"mr": None, "mr_comments": None, "mr_days": None}


def summarize(rows: list[dict]) -> dict:
    def mean(key: str) -> float | None:
        values = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        return round(statistics.mean(values), 2) if values else None
    return {
        "tasks": len(rows),
        "full_path_share": round(sum(r["path"] == "full" for r in rows) / len(rows), 2) if rows else None,
        "spec_rework_share": round(sum(r["spec_rework"] > 0 for r in rows) / len(rows), 2) if rows else None,
        **{f"mean_{k}": mean(k) for k in ("review_rounds", "deviations", "test_changes",
                                          "survivors", "promoted", "plan_edits", "lead_days", "mr_comments", "mr_days")},
    }


def table(rows: list[dict], forge: bool) -> str:
    cols = ["repo", "task", "path", "criteria", "spec_rework", "plan_edits", "review_rounds",
            "deviations", "test_changes", "survivors", "promoted", "lead_days"] + (["mr", "mr_comments", "mr_days"] if forge else [])
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join("" if r.get(c) is None else str(r[c]) for c in cols) + " |")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repos", nargs="*", default=["."], help="repositories to read (default: .)")
    parser.add_argument("--forge", action="store_true", help="also read MR/PR data with gh or glab")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)

    rows = []
    for path in args.repos:
        repo = Path(path).expanduser().resolve()
        changes = repo / "docs" / "changes"
        if not changes.is_dir():
            continue
        for folder in sorted(d for d in changes.iterdir() if d.is_dir() and (d / "plan.md").is_file()):
            row = task_metrics(repo, folder)
            if args.forge:
                row.update(forge_metrics(repo, folder.name))
            rows.append(row)

    summary = summarize(rows)
    if args.json:
        print(json.dumps({"tasks": rows, "summary": summary}, indent=2))
    elif not rows:
        print("metrics: no tasks found (docs/changes/<task>/plan.md)")
    else:
        print(table(rows, args.forge))
        print()
        for key, value in summary.items():
            print(f"{key}: {'' if value is None else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
