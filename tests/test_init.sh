#!/usr/bin/env bash
# Test suite for skills/ai-native-sdlc/scripts/init_workflow.py.
# Usage: bash tests/test_init.sh
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT="$REPO_ROOT/skills/ai-native-sdlc/scripts/init_workflow.py"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
export PYTHONPYCACHEPREFIX="$tmp/pycache"

fail=0

# --dry-run must not write anything (not even the project dir)
python3 "$SCRIPT" "$tmp/dry" --dry-run >/dev/null 2>&1 || { echo "FAIL: --dry-run exited non-zero"; fail=1; }
[[ -e "$tmp/dry" ]] && { echo "FAIL: --dry-run created the project dir"; fail=1; }

# scaffold
python3 "$SCRIPT" "$tmp/proj" >/dev/null 2>&1 || { echo "FAIL: scaffold exited non-zero"; fail=1; }
for f in CLAUDE.md REVIEW.md .gitignore scripts/check_plan_sync.py scripts/check_tdd.py scripts/check_diff_hygiene.py scripts/check_mutations.py scripts/impact_map.py; do
  [[ -e "$tmp/proj/$f" ]] || { echo "FAIL: missing $f"; fail=1; }
done
for s in check_plan_sync check_tdd check_diff_hygiene check_mutations impact_map; do
  python3 -m py_compile "$tmp/proj/scripts/$s.py" || { echo "FAIL: scaffolded $s.py does not compile"; fail=1; }
done
# the checks import each other: they must run from the scaffolded scripts/ dir
(cd "$tmp/proj" && python3 scripts/check_tdd.py --help >/dev/null 2>&1) || { echo "FAIL: scaffolded check_tdd.py does not run"; fail=1; }
for s in check_diff_hygiene check_mutations impact_map; do
  (cd "$tmp/proj" && python3 "scripts/$s.py" --help >/dev/null 2>&1) || { echo "FAIL: scaffolded $s.py does not run"; fail=1; }
done
# the intent lives in the tracker and the loop ends at the MR/PR: nothing else is scaffolded
for f in intent hooks bands.yaml evals gates workflow-graph.yaml scripts/gate_ledger.py scripts/workflow_state.py; do
  [[ -e "$tmp/proj/$f" ]] && { echo "FAIL: scaffold wrote $f"; fail=1; }
done
for section in '## Code tooling' '## Models' '## Autonomy' '## Tracker' '## Knowledge base' '## Commit and MR/PR'; do
  grep -q "$section" "$tmp/proj/CLAUDE.md" || { echo "FAIL: repository memory missing $section"; fail=1; }
done
grep -q 'Codex' "$tmp/proj/CLAUDE.md" && { echo "FAIL: repository memory still mentions Codex"; fail=1; }
[[ -f "$tmp/proj/AGENTS.md" ]] && { echo "FAIL: scaffold wrote AGENTS.md"; fail=1; }

python3 "$SCRIPT" "$tmp/proj2" >/dev/null 2>&1 || { echo "FAIL: second scaffold exited non-zero"; fail=1; }

# idempotent re-run: an existing CLAUDE.md is never overwritten without --force
echo "# my own memory" > "$tmp/proj2/CLAUDE.md"
python3 "$SCRIPT" "$tmp/proj2" >/dev/null 2>&1 || { echo "FAIL: re-run exited non-zero"; fail=1; }
[[ "$(head -1 "$tmp/proj2/CLAUDE.md")" == "# my own memory" ]] || { echo "FAIL: re-run overwrote an existing CLAUDE.md without --force"; fail=1; }

if [[ "$fail" -eq 0 ]]; then
  echo "init: all checks passed"
else
  echo "init: FAILED"
fi
[[ "$fail" -eq 0 ]]
