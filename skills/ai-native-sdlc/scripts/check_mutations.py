#!/usr/bin/env python3
"""Deterministic mutation check on the lines a change adds.

check_tdd.py proves each test fails without the whole change. This goes one
step finer: it makes small, plausible mistakes on the changed lines — flip a
comparison, swap and/or, change a constant, invert a boolean, flip + and - —
and runs the plan's Proof commands against each. A mutant the tests still
pass is a gap: a bug of that shape would ship unnoticed.

Only added lines in implementation files are mutated (tests, docs, and process
files never are), one mutant at a time, and every file is restored after each
run — also on errors and Ctrl-C.

A surviving mutant fails the check unless plan.md lists it under
"## Surviving mutants" as `path:line` with the reason it is equivalent or not
worth a test, e.g.:

    ## Surviving mutants

    - src/cart.py:12 — `>=` → `>` is equivalent: quantity is never 0 here

Usage:
    check_mutations.py [--plan <path>] [--base <rev>] [--max <n>]
                       [--timeout <seconds>] [--tests <glob>]... [--list]

Working-tree mode (default) mutates the uncommitted change; --base <rev>
mutates the lines added since <rev> on a clean checkout (MR/PR CI).
Exit codes: 0 = every mutant killed or accepted, 1 = survivors, 2 = usage or git error.
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

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
CODE_SUFFIXES = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rb",
                 ".java", ".kt", ".cs", ".php", ".rs", ".swift", ".scala")
SKIP_LINE_RE = re.compile(r"^\s*(?:#|//|/\*|\*|import\b|from\s+\S+\s+import\b|package\b|using\b|require\()")

# (name, pattern, replacement) — spaced operators only, to stay clear of
# generics, arrows, shifts, and unary signs.
OPERATORS = [
    ("== → !=", re.compile(r" == "), " != "),
    ("!= → ==", re.compile(r" != "), " == "),
    ("=== → !==", re.compile(r" === "), " !== "),
    ("!== → ===", re.compile(r" !== "), " === "),
    ("<= → <", re.compile(r" <= "), " < "),
    (">= → >", re.compile(r" >= "), " > "),
    ("< → <=", re.compile(r" < "), " <= "),
    ("> → >=", re.compile(r" > "), " >= "),
    ("and → or", re.compile(r" and "), " or "),
    ("or → and", re.compile(r" or "), " and "),
    ("&& → ||", re.compile(r" && "), " || "),
    ("|| → &&", re.compile(r" \|\| "), " && "),
    ("+ → -", re.compile(r" \+ "), " - "),
    ("- → +", re.compile(r" - "), " + "),
    ("True → False", re.compile(r"\bTrue\b"), "False"),
    ("False → True", re.compile(r"\bFalse\b"), "True"),
    ("true → false", re.compile(r"\btrue\b"), "false"),
    ("false → true", re.compile(r"\bfalse\b"), "true"),
    ("not x → x", re.compile(r"\bnot "), ""),
]
NUMBER_RE = re.compile(r"(?<![\w.])(\d+)(?![\w.])")


def added_lines(repo: Path, base: str | None) -> dict[str, list[int]]:
    """{path: new-file line numbers added by the change}."""
    args = ["diff", "--unified=0", "--no-color"] + ([f"{base}...HEAD"] if base else ["HEAD"])
    ok, out = cps._git(repo, args)
    if not ok:
        raise RuntimeError(out)
    lines: dict[str, list[int]] = {}
    current, number = None, 0
    for line in out.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
            continue
        match = HUNK_RE.match(line)
        if match:
            number = int(match.group(1))
            continue
        if current and line.startswith("+"):
            lines.setdefault(current, []).append(number)
            number += 1
    if base is None:
        ok, untracked = cps._git(repo, ["ls-files", "--others", "--exclude-standard"])
        for path in untracked.splitlines() if ok else []:
            try:
                count = len((repo / path).read_text(encoding="utf-8").splitlines())
            except (OSError, UnicodeDecodeError):
                continue
            lines[path] = list(range(1, count + 1))
    return lines


def mutants_for(line: str) -> list[tuple[str, str]]:
    """[(operator name, mutated line)] — every applicable single mutation."""
    if SKIP_LINE_RE.match(line) or not line.strip():
        return []
    out = []
    for name, pattern, replacement in OPERATORS:
        if pattern.search(line):
            out.append((name, pattern.sub(replacement, line, count=1)))
    number = NUMBER_RE.search(line)
    if number and not re.search(r"""["']""", line[:number.start()]):
        value = int(number.group(1))
        out.append((f"{value} → {value + 1}",
                    line[:number.start()] + str(value + 1) + line[number.end():]))
    return out


def plan_mutants(repo: Path, changed: dict[str, list[int]], tests: list[str]) -> list[tuple[str, int, str, str]]:
    """[(path, line number, operator, mutated line)] in file/line order."""
    result = []
    for path in sorted(changed):
        if not path.endswith(CODE_SUFFIXES) or tdd.is_test_path(path, tests) \
                or cps._is_process_path(path, []):
            continue
        try:
            source = (repo / path).read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number in changed[path]:
            if 1 <= number <= len(source):
                for name, mutated in mutants_for(source[number - 1]):
                    result.append((path, number, name, mutated))
    return result


def accepted(plan_text: str) -> set[str]:
    return {m.group(0) for line in tdd.section(plan_text, "Surviving mutants")
            for m in re.finditer(r"[\w./-]+:\d+", line)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plan", default=None, help="plan path (default: the task's docs/changes/*/plan.md)")
    parser.add_argument("--base", default=None, help="committed mode: mutate lines added since this revision")
    parser.add_argument("--max", type=int, default=25, help="most mutants to run (default 25)")
    parser.add_argument("--timeout", type=int, default=300, help="seconds per command (default 300)")
    parser.add_argument("--tests", action="append", default=[], help="extra test-file glob")
    parser.add_argument("--list", action="store_true", help="print the mutants without running them")
    args = parser.parse_args(argv)

    repo = Path.cwd()
    if args.base:
        ok, status = cps._git(repo, ["status", "--porcelain"])
        if not ok or status.strip():
            print("error: --base needs a clean working tree", file=sys.stderr)
            return 2
    try:
        changed = added_lines(repo, args.base)
    except RuntimeError as exc:
        print(f"error: git diff failed: {exc}", file=sys.stderr)
        return 2
    plan_path, error = cps._resolve_plan(repo, sorted(changed), args.plan, use_branch=True)
    if error or not plan_path or not (repo / plan_path).is_file():
        print(f"error: {error or 'no plan found; pass --plan docs/changes/<task>/plan.md'}", file=sys.stderr)
        return 2
    plan_text = (repo / plan_path).read_text(encoding="utf-8")
    commands = [cmd for _, cmd in tdd.parse_proof(plan_text) if cmd]

    mutants = plan_mutants(repo, changed, args.tests)
    skipped = max(0, len(mutants) - args.max)
    mutants = mutants[:args.max]
    if args.list:
        for path, number, name, mutated in mutants:
            print(f"{path}:{number}  {name}  {mutated.strip()}")
        return 0
    if not mutants:
        print("check_mutations: no mutable lines in the change")
        return 0
    if not commands:
        print(f"error: no Proof commands in {plan_path} to run against the mutants", file=sys.stderr)
        return 2

    allowed = accepted(plan_text)
    survivors = killed = 0
    for path, number, name, mutated in mutants:
        file = repo / path
        original = file.read_bytes()
        lines = original.decode("utf-8").splitlines(keepends=True)
        ending = lines[number - 1][len(lines[number - 1].rstrip("\r\n")):]
        lines[number - 1] = mutated + ending
        try:
            file.write_text("".join(lines), encoding="utf-8")
            dead = any(tdd.run(repo, command, args.timeout)[0] != 0 for command in commands)
        finally:
            file.write_bytes(original)
        where = f"{path}:{number}"
        if dead:
            killed += 1
            print(f"ok   killed    {where}  {name}")
        elif where in allowed:
            print(f"ok   accepted  {where}  {name} (listed under ## Surviving mutants)")
        else:
            survivors += 1
            print(f"FAIL survived  {where}  {name}  →  {mutated.strip()[:100]}")

    total = killed + survivors
    score = 100 if total == 0 else round(100 * killed / total)
    note = f", {skipped} not run (raise --max)" if skipped else ""
    print(f"check_mutations: {len(mutants)} mutant(s), {killed} killed, {survivors} survived "
          f"(score {score}%){note}")
    if survivors:
        print("add a test that fails for each survivor, or list it under "
              f"## Surviving mutants in {plan_path} with the reason")
    return 1 if survivors else 0


if __name__ == "__main__":
    raise SystemExit(main())
