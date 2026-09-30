#!/usr/bin/env python3
"""Deterministic impact map: what a change can break, and how risky each file is.

For each implementation file a change touches, reports:

  - dependents — files that import it (Python `import`/`from`, JS/TS
    `import`/`require`), found with `git grep` over tracked files;
  - callers — files that use the functions and classes the change adds or
    edits (by whole-word match; a lead to read, not a proof);
  - history — commits in the last 12 months and the share whose subject says
    fix/bug/hotfix/revert/regression;
  - risk — high, mid, or low from fan-in (dependents + callers) and fix rate.

Run it twice:
  - in Build, before writing code, with --from-plan: maps the files plan.md's
    "Files that change" lists, so the plan's "## Impact" names the regression
    tests the risky paths need;
  - in Review, with --check: fails when a high-risk file the change touches is
    not named under plan.md's "## Impact" with how its regression is covered.

Usage:
    impact_map.py [--from-plan] [--base <rev>] [--plan <path>] [--files <path>...]
                  [--months <n>] [--json] [--check]

Exit codes: 0 = ok, 1 = --check failed, 2 = usage or git error.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_mutations as cmut  # noqa: E402
import check_plan_sync as cps  # noqa: E402
import check_tdd as tdd  # noqa: E402

FIX_RE = re.compile(r"\b(fix|fixes|fixed|bug|hotfix|revert|regression)\b", re.I)
SYMBOL_RES = [
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*class\s+([A-Za-z_]\w*)"),
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\(|function|[A-Za-z_$][\w$]*\s*=>)"),
    re.compile(r"^\s*(?:export\s+)?(?:interface|type|enum)\s+([A-Za-z_$][\w$]*)"),
    re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)"),
]
PY_SUFFIXES = (".py",)
JS_SUFFIXES = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")


def _git(repo: Path, *args: str) -> tuple[bool, str]:
    return cps._git(repo, list(args))


class Corpus:
    """The repo's tracked code files, read once — searched in Python so the
    regex dialect is the same on every platform (git grep's is not)."""

    def __init__(self, repo: Path):
        ok, out = _git(repo, "ls-files")
        self.files: dict[str, list[str]] = {}
        for path in out.splitlines() if ok else []:
            if not path.endswith(cmut.CODE_SUFFIXES):
                continue
            try:
                self.files[path] = (repo / path).read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue

    def grep(self, pattern: re.Pattern) -> set[str]:
        return {path for path, lines in self.files.items() if any(pattern.search(l) for l in lines)}


def import_pattern(path: str) -> re.Pattern | None:
    """A regex matching lines that import `path`."""
    stem = Path(path).stem
    if path.endswith(PY_SUFFIXES):
        if stem == "__init__":
            stem = Path(path).parent.name
        return re.compile(rf"^\s*(?:from|import)\s+[\w.]*\b{re.escape(stem)}\b")
    if path.endswith(JS_SUFFIXES):
        if stem == "index":
            stem = Path(path).parent.name
        return re.compile(rf"(?:from|require\(|import\()\s*['\"][^'\"]*\b{re.escape(stem)}(?:\.[a-z]+)?['\"]")
    return None


def symbols(repo: Path, path: str, lines: list[int] | None) -> list[str]:
    try:
        source = (repo / path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []
    wanted = range(1, len(source) + 1) if lines is None else lines
    found = []
    for number in wanted:
        if 1 <= number <= len(source):
            for pattern in SYMBOL_RES:
                match = pattern.match(source[number - 1])
                if match and len(match.group(1)) >= 3 and not match.group(1).startswith("__"):
                    found.append(match.group(1))
    return sorted(set(found))


def history(repo: Path, path: str, months: int) -> tuple[int, int]:
    ok, out = _git(repo, "log", f"--since={months}.months", "--format=%s", "--", path)
    subjects = [s for s in out.splitlines() if s.strip()] if ok else []
    return len(subjects), sum(1 for s in subjects if FIX_RE.search(s))


def risk(fan_in: int, commits: int, fixes: int) -> str:
    rate = fixes / commits if commits else 0.0
    if fan_in >= 5 or (commits >= 5 and rate >= 0.3):
        return "high"
    if fan_in >= 2 or (commits >= 3 and rate >= 0.2):
        return "mid"
    return "low"


def analyze(repo: Path, targets: dict[str, list[int] | None], months: int, tests: list[str]) -> list[dict]:
    corpus = Corpus(repo)
    rows = []
    for path in sorted(targets):
        if not path.endswith(cmut.CODE_SUFFIXES) or tdd.is_test_path(path, tests) \
                or cps._is_process_path(path, []):
            continue
        pattern = import_pattern(path)
        dependents = {p for p in corpus.grep(pattern) if p != path} if pattern else set()
        callers: dict[str, list[str]] = {}
        for name in symbols(repo, path, targets[path]):
            files = sorted(p for p in corpus.grep(re.compile(rf"\b{re.escape(name)}\b")) if p != path)
            if files:
                callers[name] = files
        users = dependents | {p for files in callers.values() for p in files}
        test_users = sorted(p for p in users if tdd.is_test_path(p, tests))
        code_users = sorted(p for p in users if not tdd.is_test_path(p, tests))
        commits, fixes = history(repo, path, months)
        rows.append({
            "path": path,
            "risk": risk(len(code_users), commits, fixes),
            "fan_in": len(code_users),
            "dependents": sorted(p for p in dependents if not tdd.is_test_path(p, tests)),
            "callers": callers,
            "tests_touching": test_users,
            "imports_resolved": pattern is not None,
            "commits": commits,
            "fix_rate": round(fixes / commits, 2) if commits else 0.0,
        })
    order = {"high": 0, "mid": 1, "low": 2}
    return sorted(rows, key=lambda r: (order[r["risk"]], -r["fan_in"], r["path"]))


def plan_targets(repo: Path, plan_text: str) -> dict[str, list[int] | None]:
    try:
        entries = cps._manifest_entries(plan_text)
    except ValueError:
        return {}
    ok, files = _git(repo, "ls-files")
    tracked = files.splitlines() if ok else []
    targets: dict[str, list[int] | None] = {}
    for entry in entries:
        for path in tracked:
            if fnmatch.fnmatch(path, entry):
                targets[path] = None
        if not any(ch in entry for ch in "*?[") and (repo / entry).is_file():
            targets.setdefault(entry, None)
    return targets


def report(rows: list[dict]) -> str:
    if not rows:
        return "impact_map: no implementation files to map"
    out = ["| File | Risk | Fan-in | Commits (12m) | Fix rate | Tests touching |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['path']} | {r['risk']} | {r['fan_in']} | {r['commits']} | "
                   f"{int(r['fix_rate'] * 100)}% | {len(r['tests_touching'])} |")
    for r in rows:
        if r["dependents"] or r["callers"]:
            out.append(f"\n{r['path']} ({r['risk']})")
            for dep in r["dependents"][:10]:
                out.append(f"  imported by {dep}")
            for name, files in sorted(r["callers"].items()):
                shown = ", ".join(files[:5]) + (" …" if len(files) > 5 else "")
                out.append(f"  {name}() used in {shown}")
    for r in rows:
        if not r["imports_resolved"]:
            out.append(f"\nnote: imports of {r['path']} not resolved (Python and JS/TS only); "
                       "its fan-in counts callers by name alone")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-plan", action="store_true",
                        help="map the files plan.md lists (before the change exists)")
    parser.add_argument("--base", default=None, help="map the change since this revision (committed)")
    parser.add_argument("--plan", default=None, help="plan path (default: the task's docs/changes/*/plan.md)")
    parser.add_argument("--files", nargs="*", default=None, help="map these files instead")
    parser.add_argument("--months", type=int, default=12, help="history window (default 12)")
    parser.add_argument("--tests", action="append", default=[], help="extra test-file glob")
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument("--check", action="store_true",
                        help="fail when a high-risk file is not named under plan.md ## Impact")
    args = parser.parse_args(argv)

    repo = Path.cwd()
    try:
        changed = cmut.added_lines(repo, args.base)
    except RuntimeError as exc:
        print(f"error: git diff failed: {exc}", file=sys.stderr)
        return 2
    plan_path, _ = cps._resolve_plan(repo, sorted(changed), args.plan, use_branch=True)
    plan_text = (repo / plan_path).read_text(encoding="utf-8") \
        if plan_path and (repo / plan_path).is_file() else None

    if args.files is not None:
        targets: dict[str, list[int] | None] = {p: None for p in args.files}
    elif args.from_plan:
        if plan_text is None:
            print("error: --from-plan needs a plan (pass --plan)", file=sys.stderr)
            return 2
        targets = plan_targets(repo, plan_text)
    else:
        targets = dict(changed)

    rows = analyze(repo, targets, args.months, args.tests)
    print(json.dumps(rows, indent=2) if args.json else report(rows))

    if args.check:
        if plan_text is None:
            print("error: --check needs a plan (pass --plan)", file=sys.stderr)
            return 2
        impact = "\n".join(tdd.section(plan_text, "Impact"))
        missing = [r["path"] for r in rows if r["risk"] == "high" and r["path"] not in impact]
        for path in missing:
            print(f"FAIL high-risk {path} is not named under ## Impact in {plan_path} "
                  "with how its regression is covered")
        return 1 if missing else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
