#!/usr/bin/env python3
"""Run the eval suite locally or in CI (Phase 4 - Test).

Usage:
    python3 run_evals.py evals/ [--workdir DIR] [--min-pass-rate 0.9]
           [--record] [--record-dir evals/results] [--no-agent] [--verbose]

Eval files are JSON (see assets/evals.example.json):
{
  "name": "duplicate import regression",            # optional; defaults to file name
  "prompt": "Fix the duplicate import in app/main.py",  # used only when an agent CLI is configured
  "agent": {"cli": "claude -p"},                    # optional; env AGENT_CLI overrides
  "checks": [
    {"run": "python -m pytest -q", "expect_exit": 0, "contains": "passed"},
    "git diff --stat"                                # plain string = run, must exit 0
  ]
}

A check passes when the command exits `expect_exit` (default 0) and stdout+
stderr contains every `contains` substring. The suite fails (exit 1) when the
pass rate drops below --min-pass-rate, so CI can gate config changes on it.
--record appends one JSON line per run to evals/results/results.jsonl.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def load_evals(evals_dir: str) -> list[dict]:
    out: list[dict] = []
    for p in sorted(Path(evals_dir).glob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"SKIP {p.name}: invalid JSON ({exc})")
            continue
        if not isinstance(data.get("checks"), list) or not data["checks"]:
            print(f"SKIP {p.name}: missing non-empty 'checks' list")
            continue
        data.setdefault("name", p.stem)
        data["_file"] = p.name
        out.append(data)
    return out


def run_check(check: dict | str, workdir: str) -> tuple[bool, str]:
    if isinstance(check, str):
        cmd, expect_exit, contains = check, 0, []
    else:
        cmd = check.get("run", "")
        expect_exit = check.get("expect_exit", 0)
        contains = check.get("contains", []) or []
    if isinstance(contains, str):
        contains = [contains]
    if not cmd:
        return False, "empty check"
    try:
        res = subprocess.run(
            cmd, shell=True, cwd=workdir, capture_output=True, text=True, timeout=600
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    output = res.stdout + res.stderr
    missing = [c for c in contains if c not in output]
    ok_result = res.returncode == expect_exit and not missing
    detail = f"exit={res.returncode} (want {expect_exit})"
    if missing:
        detail += f" missing={missing}"
    return ok_result, detail


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evals_dir", help="directory containing evals/*.json")
    parser.add_argument("--workdir", default=".", help="directory checks run in (default: current dir)")
    parser.add_argument("--min-pass-rate", type=float, default=0.0, help="fail below this pass rate (0..1)")
    parser.add_argument("--record", action="store_true", help="append a run record to --record-dir")
    parser.add_argument("--record-dir", default="evals/results", help="where run records are appended")
    parser.add_argument("--no-agent", action="store_true", help="skip agent invocation, run checks directly")
    parser.add_argument("--verbose", action="store_true", help="print per-check detail")
    args = parser.parse_args(argv)

    evals = load_evals(args.evals_dir)
    if not evals:
        print(f"no eval files found in {args.evals_dir}")
        return 2

    total = passed = 0
    for ev in evals:
        # Optional: run the prompt through an agent CLI first (e.g. `claude -p`).
        if not args.no_agent and ev.get("agent"):
            cli = os.environ.get("AGENT_CLI") or ev["agent"].get("cli")
            if cli:
                cmd = cli.split() + [str(ev.get("prompt", ""))]
                try:
                    subprocess.run(cmd, cwd=args.workdir, capture_output=True, text=True, timeout=900)
                except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
                    print(f"WARN {ev['name']}: agent run failed ({exc}); checks run against current state")

        results = [run_check(c, args.workdir) for c in ev["checks"]]
        n_ok = sum(1 for ok, _ in results if ok)
        total += len(results)
        passed += n_ok
        status = "PASS" if n_ok == len(results) else "FAIL"
        print(f"{status} {ev['name']} ({n_ok}/{len(results)})")
        if args.verbose:
            for c, (ok, detail) in zip(ev["checks"], results):
                label = c if isinstance(c, str) else c.get("run")
                print(f"    {'ok ' if ok else 'XX '}{label}  {'' if ok else detail}")

    rate = passed / total if total else 0.0
    print(f"pass rate: {rate:.0%} ({passed}/{total})")

    if args.record:
        out_dir = Path(args.record_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "passed": passed,
            "total": total,
            "pass_rate": round(rate, 4),
        }
        with open(out_dir / "results.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    if rate < args.min_pass_rate:
        print(f"below --min-pass-rate {args.min_pass_rate:.0%}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
