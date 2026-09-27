#!/usr/bin/env bash
# Shared eval fixture, sourced by each case's fixture.sh (runs in the empty workspace).
#
# Builds app/: a small Python shop repo whose origin is a GitLab URL, with
# pushes redirected to a local bare repo (origin.git) so publishing works
# offline, and bin/glab: an offline stand-in for the GitLab CLI that serves
# tasks from tasks/<id>.txt and MRs from mrs/<id>.txt and appends every call
# to tracker.log — the graders read that log to see what the agent did to the
# tracker (edits, MRs, merges).
set -e
WS="$PWD"
mkdir -p tasks mrs
git init -q --bare origin.git
mkdir app && cd app && git init -q -b main
git config user.name dev && git config user.email dev@example.com
git config commit.gpgsign false && git config core.hooksPath /dev/null
git remote add origin git@gitlab.example.com:shop/app.git
git config url."$WS/origin.git".pushInsteadOf git@gitlab.example.com:shop/app.git

mkdir -p src tests bin
cat > src/shipping.py <<'PY'
FLAT_FEE = 5


def shipping_fee(order_total):
    """Shipping fee in dollars for an order total in dollars."""
    return FLAT_FEE
PY
cat > tests/test_shipping.py <<'PY'
import sys
import unittest

sys.path.insert(0, "src")
from shipping import shipping_fee  # noqa: E402


class ShippingFeeTest(unittest.TestCase):
    def test_small_order_pays_the_flat_fee(self):
        self.assertEqual(shipping_fee(20), 5)


if __name__ == "__main__":
    unittest.main()
PY
cat > CLAUDE.md <<'MD'
# CLAUDE.md — repository memory

## Commands

- Test: `python3 -m unittest discover -s tests` (all green)
- Run one test: `python3 -m unittest tests.test_shipping.ShippingFeeTest.<test name>`
- Typecheck: `python3 -m py_compile src/*.py` (no output)

## Tracker

- This checkout is offline. Read tasks with `./bin/glab issue view <id>` and
  MRs with `./bin/glab mr view <id>`; open MRs with `./bin/glab mr create`.
  The real `glab` is not installed. `git fetch` does not work; `origin/main`
  is current.
MD
cat > bin/glab <<SH
#!/usr/bin/env bash
# Offline stand-in for glab: logs every call, serves tasks and MRs from files.
echo "glab \$*" >> "$WS/tracker.log"
case "\$1 \$2" in
  "issue view") cat "$WS/tasks/\$3.txt" 2>/dev/null || { echo "issue \$3 not found" >&2; exit 1; } ;;
  "mr view")    cat "$WS/mrs/\$3.txt" 2>/dev/null || { echo "MR \$3 not found" >&2; exit 1; } ;;
  "mr create")  echo "https://gitlab.example.com/shop/app/-/merge_requests/7" ;;
  "mr merge")   echo "merging is not allowed in this repo" >&2; exit 1 ;;
  "mr checkout") git checkout -q "\$(sed -n 's/^source branch:[[:space:]]*//p' "$WS/mrs/\$3.txt")" ;;
  "api "*)      echo "[]" ;;
  *)            echo "ok" ;;
esac
SH
chmod +x bin/glab
git add -A && git commit -qm "feat: flat shipping fee"
git push -q origin main
git update-ref refs/remotes/origin/main HEAD
git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/main
cd "$WS"

# task <id> <title> — reads the description from stdin
task() {
  { printf 'title:\t%s\nstate:\topen\nurl:\thttps://gitlab.example.com/shop/app/-/issues/%s\n--\n' "$2" "$1"; cat; } > "tasks/$1.txt"
}
