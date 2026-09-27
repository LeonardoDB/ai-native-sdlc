#!/usr/bin/env python3
"""Claude Code PreToolUse hook: the workflow's red lines, enforced outside the prompt.

Reads the hook event (JSON) on stdin. For Bash commands:

  always blocked
    - merging an MR/PR (`glab mr merge`, `gh pr merge`) — the loop ends at the
      opened MR/PR; the team merges
    - pushing to the default branch (`git push … main`, `HEAD:main`, …)
    - bypassing hooks or signing (`--no-verify`, `--no-gpg-sign`)
    - force-pushing without a lease (`--force`, `-f`; `--force-with-lease` is fine)

  gated on the checks, for a workflow task (the branch has docs/changes/<task>/plan.md)
    - `git push`, `glab mr create`, `gh pr create` pass only when the tree is
      committed and check_plan_sync, check_tdd, check_diff_hygiene, and
      impact_map --check pass against the default branch (set
      SDLC_GATE_MUTATIONS=1 to add check_mutations). Repos and branches with no
      task plan are left alone.

There is deliberately no Stop hook: a red test is a normal state in the middle
of a TDD slice, and the agent must be free to stop and ask for approval.

Exit codes follow Claude Code's hook contract: 0 = allow, 2 = block (the
reason on stderr is shown to the agent).

Wire it in .claude/settings.json (or the plugin's hooks/hooks.json):

    {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": "python3 <skill>/hooks/gate.py"}]}]}}
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
SKILL_SCRIPTS = HOOK_DIR.parent / "scripts"
SEGMENT = r"[^;&|\n]*"

MERGE_RE = re.compile(r"\b(?:glab\s+mr\s+merge|gh\s+pr\s+merge)\b")
PUSH_RE = re.compile(r"\bgit\s+push\b")
PUBLISH_RE = re.compile(r"\bgit\s+push\b|\bglab\s+mr\s+create\b|\bgh\s+pr\s+create\b")
NO_VERIFY_RE = re.compile(r"\bgit\s+(?:commit|push|merge|rebase)\b" + SEGMENT + r"(?:--no-verify|--no-gpg-sign)\b")
FORCE_RE = re.compile(r"\bgit\s+push\b" + SEGMENT + r"(?:\s--force(?!-with-lease)\b|\s-f\b|\s\+\S)")


def git(cwd: Path, *args: str) -> tuple[bool, str]:
    try:
        res = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return False, str(exc)
    return res.returncode == 0, res.stdout.strip()


def default_branch(cwd: Path) -> tuple[str | None, str | None]:
    """(branch name, revision to compare against)."""
    ok, head = git(cwd, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if ok and "/" in head:
        return head.split("/", 1)[1], head
    for name in ("main", "master", "develop"):
        if git(cwd, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}")[0]:
            return name, name
    return None, None


def pushes_to(command: str, branch: str) -> bool:
    for match in re.finditer(r"\bgit\s+push\b(" + SEGMENT + ")", command):
        args = match.group(1).split()
        refs = [a for a in args if not a.startswith("-")][1:]  # after the remote
        if any(ref == branch or ref.endswith(f":{branch}") or ref.endswith(f":refs/heads/{branch}")
               for ref in refs):
            return True
    return False


def task_plan(cwd: Path) -> Path | None:
    ok, branch = git(cwd, "branch", "--show-current")
    leaf = branch.rsplit("/", 1)[-1].lower() if ok else ""
    changes = cwd / "docs" / "changes"
    if not leaf or not changes.is_dir():
        return None
    matches = [d for d in changes.iterdir()
               if d.is_dir() and (d / "plan.md").is_file()
               and (leaf == d.name.lower() or leaf.startswith(d.name.lower() + "-"))]
    return max(matches, key=lambda d: len(d.name)) / "plan.md" if matches else None


def scripts_dir(cwd: Path) -> Path:
    local = cwd / "scripts"
    return local if (local / "check_tdd.py").is_file() else SKILL_SCRIPTS


def run_checks(cwd: Path, plan: Path, base: str) -> list[str]:
    scripts = scripts_dir(cwd)
    rel_plan = str(plan.relative_to(cwd))
    checks = [
        ["check_plan_sync.py", "--base", base, "--head", "HEAD", "--plan", rel_plan],
        ["check_tdd.py", "--base", base, "--plan", rel_plan],
        ["check_diff_hygiene.py", "--base", base, "--plan", rel_plan],
        ["impact_map.py", "--base", base, "--plan", rel_plan, "--check"],
    ]
    if os.environ.get("SDLC_GATE_MUTATIONS") == "1":
        checks.append(["check_mutations.py", "--base", base, "--plan", rel_plan])
    failures = []
    for script, *args in checks:
        try:
            res = subprocess.run([sys.executable, str(scripts / script), *args], cwd=cwd,
                                 capture_output=True, text=True, timeout=1800)
        except subprocess.TimeoutExpired:
            failures.append(f"{script}: timed out")
            continue
        if res.returncode != 0:
            lines = [l for l in (res.stdout + res.stderr).splitlines() if "FAIL" in l or "error" in l]
            failures.append(f"{script}: " + ("; ".join(lines[:5]) or f"exit {res.returncode}"))
    return failures


def decide(event: dict) -> tuple[bool, str]:
    """(allowed, reason)."""
    if event.get("tool_name") != "Bash":
        return True, ""
    command = (event.get("tool_input") or {}).get("command") or ""
    cwd = Path(event.get("cwd") or os.getcwd())

    if MERGE_RE.search(command):
        return False, ("merging is outside this workflow: the loop ends at the opened MR/PR, "
                       "and the team reviews and merges")
    if NO_VERIFY_RE.search(command):
        return False, "never bypass hooks or signing (--no-verify / --no-gpg-sign)"
    if FORCE_RE.search(command):
        return False, "force-push only with --force-with-lease"
    branch, base = default_branch(cwd)
    if PUSH_RE.search(command) and branch and pushes_to(command, branch):
        return False, f"never push to the default branch ({branch}); push the task branch and open an MR/PR"

    if not PUBLISH_RE.search(command):
        return True, ""
    plan = task_plan(cwd)
    if plan is None or base is None:
        return True, ""
    ok, status = git(cwd, "status", "--porcelain")
    if ok and status:
        return False, "commit the change before pushing or opening the MR/PR (the working tree is not clean)"
    failures = run_checks(cwd, plan, base)
    if failures:
        return False, "the workflow's checks fail — fix them before publishing:\n  " + "\n  ".join(failures)
    return True, ""


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # never block on a malformed event
    allowed, reason = decide(event)
    if not allowed:
        print(f"ai-native-sdlc gate: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
