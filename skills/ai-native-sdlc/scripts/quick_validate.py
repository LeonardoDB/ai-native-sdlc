#!/usr/bin/env python3
"""Validate the ai-native-sdlc skill/plugin bundle (self-check).

Usage:
    python3 quick_validate.py [skill-dir]     (default: ./skills/ai-native-sdlc)

Checks (stdlib only; PyYAML is used when available, otherwise a structural
YAML sanity check):
  1. SKILL.md exists with name/description/version frontmatter.
  2. Every relative path linked from SKILL.md exists.
  3. plugin.json (repo root) name/version match the skill frontmatter.
  4. Every file the skill promises exists.
  5. YAML/JSON assets parse.
  6. Shell assets pass `bash -n`.
  7. The scaffold script smoke-scaffolds into a temp dir.
  8. Python scripts compile.

Exit 0 on success, 1 on any failure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

# Files the skill promises, beyond what markdown links already cover.
PROMISED = [
    "SKILL.md",
    "references/playbook.md",
    "references/adoption.md",
    "references/trackers.md",
    "references/agents/explorer.md",
    "references/agents/reviewer.md",
    "references/knowledge.md",
    "references/debugging.md",
    "references/feedback.md",
    "scripts/init_workflow.py",
    "scripts/tracker_link.py",
    "scripts/check_plan_sync.py",
    "scripts/check_tdd.py",
    "scripts/check_diff_hygiene.py",
    "scripts/check_mutations.py",
    "scripts/impact_map.py",
    "scripts/metrics.py",
    "hooks/gate.py",
    "assets/intent.md",
    "assets/spec.md",
    "assets/plan.md",
    "assets/CLAUDE.md",
    "assets/REVIEW.md",
    "assets/PULL_REQUEST_TEMPLATE.md",
    "assets/.gitignore",
]

failures: list[str] = []
passes: list[str] = []


def ok(msg: str) -> None:
    passes.append(msg)
    print(f"  PASS: {msg}")


def bad(msg: str) -> None:
    failures.append(msg)
    print(f"  FAIL: {msg}")


def check(condition: bool, msg: str) -> None:
    (ok if condition else bad)(msg)


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            out[k.strip()] = v.strip().strip('"\'')
    return out


def yaml_ok(path: Path) -> bool:
    """Parse YAML with PyYAML if available; else structural sanity check."""
    try:
        import yaml  # type: ignore

        with open(path, encoding="utf-8") as fh:
            yaml.safe_load(fh)
        return True
    except ImportError:
        text = path.read_text(encoding="utf-8")
        if "\t" in text:
            return False
        if text.count("{") != text.count("}") or text.count("[") != text.count("]"):
            return False
        return True
    except Exception:
        return False


def run(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str]:
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=180,
            env=env,
        )
        return res.returncode, (res.stdout + res.stderr).strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return -1, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "skill_dir",
        nargs="?",
        default="skills/ai-native-sdlc",
        help="path to the skill folder (default: skills/ai-native-sdlc)",
    )
    args = parser.parse_args()

    skill = Path(args.skill_dir).resolve()
    repo_root = skill.parent.parent
    print(f"Validating skill at {skill} (repo root: {repo_root})")

    # 1. SKILL.md frontmatter
    skill_md = skill / "SKILL.md"
    check(skill_md.is_file(), "SKILL.md exists")
    if not skill_md.is_file():
        bad("cannot continue without SKILL.md")
        return 1
    fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    check(bool(fm.get("name")), "SKILL.md has a name")
    check(bool(fm.get("description")), "SKILL.md has a description")
    check(bool(fm.get("version")), "SKILL.md has a version")

    # 2. Every relative markdown link resolves.
    text = skill_md.read_text(encoding="utf-8")
    for link in LINK_RE.findall(text):
        if link.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = (skill / link).resolve()
        check(target.exists(), f"linked file exists: {link}")

    # 3. Claude Code plugin + marketplace consistency.
    claude = repo_root / ".claude-plugin" / "plugin.json"
    market = repo_root / ".claude-plugin" / "marketplace.json"
    if claude.is_file():
        try:
            data = json.loads(claude.read_text(encoding="utf-8"))
            check(data.get("name") == fm.get("name"), "Claude plugin.json name matches SKILL.md")
            check(data.get("version") == fm.get("version"), "Claude plugin.json version matches SKILL.md")
            check((repo_root / "hooks" / "hooks.json").is_file(),
                  "Claude plugin hooks/hooks.json exists (auto-loaded; not listed in plugin.json)")
            check("hooks" not in data or data["hooks"] not in ("./hooks/hooks.json", ["./hooks/hooks.json"]),
                  "plugin.json does not re-list the default hooks/hooks.json (it would load twice)")
        except json.JSONDecodeError as exc:
            bad(f"Claude plugin.json is not valid JSON: {exc}")
    else:
        bad("Claude plugin.json not found")
    if market.is_file():
        try:
            entries = json.loads(market.read_text(encoding="utf-8")).get("plugins") or []
            entry = next((p for p in entries if p.get("name") == fm.get("name")), None)
            check(entry is not None, "marketplace.json lists the plugin")
            if entry:
                check(entry.get("version") in (None, fm.get("version")), "marketplace.json version matches SKILL.md")
        except json.JSONDecodeError as exc:
            bad(f"marketplace.json is not valid JSON: {exc}")

    # 3b. Eval cases are complete (claude plugin eval format).
    evals = repo_root / "evals"
    for case in sorted(p for p in evals.iterdir() if p.is_dir() and p.name[:1].isdigit()) if evals.is_dir() else []:
        check((case / "case.yaml").is_file() and (case / "prompt.md").is_file()
              and any((case / "graders").glob("*.md")), f"eval case complete: {case.name}")

    # 4. Promised files exist.
    for rel in PROMISED:
        check((skill / rel).exists(), f"promised file exists: {rel}")

    # 5. YAML/JSON assets parse.
    for path in sorted((skill / "assets").rglob("*")):
        if path.suffix in (".yaml", ".yml"):
            check(yaml_ok(path), f"YAML parses: {path.name}")
        elif path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
                ok(f"JSON parses: {path.name}")
            except json.JSONDecodeError as exc:
                bad(f"JSON parses: {path.name} ({exc})")

    # 6. Shell syntax.
    for path in sorted(list((skill / "assets").glob("*.sh")) + list((skill / "scripts").glob("*.sh"))):
        code, _ = run(["bash", "-n", str(path)])
        check(code == 0, f"bash -n: {path.name}")

    # 7. Scaffold smoke test.
    with tempfile.TemporaryDirectory() as td:
        smoke = Path(td) / "smoke"
        code, out = run(["python3", str(skill / "scripts" / "init_workflow.py"), str(smoke)])
        check(code == 0, "init_workflow.py scaffold smoke test")
        check((smoke / "CLAUDE.md").is_file(), "scaffold writes CLAUDE.md")
        for name in ("check_plan_sync.py", "check_tdd.py", "check_diff_hygiene.py", "check_mutations.py", "impact_map.py"):
            check((smoke / "scripts" / name).is_file(), f"scaffold writes {name}")
        check(not (smoke / "intent").exists(), "scaffold writes no intent/ (intent lives in the tracker)")
        check(not (smoke / "hooks").exists(), "scaffold writes no release hook (the loop ends at the MR/PR)")

    # 8. Python scripts compile cleanly.
    with tempfile.TemporaryDirectory(prefix="quickvalidate-pycache-") as pycache:
        compile_env = {**os.environ, "PYTHONPYCACHEPREFIX": pycache}
        for script in (
            "init_workflow.py",
            "tracker_link.py",
            "check_plan_sync.py",
            "check_tdd.py",
            "check_diff_hygiene.py",
            "check_mutations.py",
            "impact_map.py",
            "metrics.py",
            "gate.py",
            "quick_validate.py",
        ):
            code, _ = run(
                ["python3", "-m", "py_compile", str(skill / ("hooks" if script == "gate.py" else "scripts") / script)],
                env=compile_env,
            )
            check(code == 0, f"py_compile: {script}")

    print()
    print(f"quick_validate: {len(passes)} passed, {len(failures)} failed")
    if failures:
        print("Run the failing checks above; keep plugin.json and SKILL.md in sync.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
