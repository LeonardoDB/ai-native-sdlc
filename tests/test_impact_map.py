"""Tests for scripts/impact_map.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest

from test_check_tdd import SCRIPTS, Repo, git

IMPACT = SCRIPTS / "impact_map.py"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("impact_map", IMPACT)
im = importlib.util.module_from_spec(spec)
spec.loader.exec_module(im)

PLAN = """\
# Pricing

- Status: Approved

## Files that change

- src/pricing.py

## Impact

{impact}
"""


class UnitTests(unittest.TestCase):
    def test_risk_tiers(self) -> None:
        self.assertEqual(im.risk(fan_in=5, commits=0, fixes=0), "high")
        self.assertEqual(im.risk(fan_in=0, commits=10, fixes=4), "high")
        self.assertEqual(im.risk(fan_in=2, commits=0, fixes=0), "mid")
        self.assertEqual(im.risk(fan_in=0, commits=1, fixes=1), "low")

    def test_import_patterns(self) -> None:
        self.assertIsNotNone(im.import_pattern("src/pricing.py"))
        self.assertIsNotNone(im.import_pattern("web/cart/index.ts"))
        self.assertIsNone(im.import_pattern("README.md"))


class ImpactMapTests(Repo):
    def build(self, users: int) -> None:
        self.write("src/pricing.py", "def price(x):\n    return x\n")
        for n in range(users):
            self.write(f"src/user{n}.py", "from pricing import price\n\nprint(price(1))\n")
        self.write("web/cart.ts", "import { total } from './lib/total';\n")
        self.write("web/lib/total.ts", "export function total(a: number) { return a; }\n")
        self.write("tests/test_pricing.py", "from pricing import price\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "fix: pricing rounding")

    def test_python_dependents_and_risk(self) -> None:
        self.build(users=5)
        self.write("src/pricing.py", "def price(x):\n    return round(x, 2)\n")
        res = self.run_script(IMPACT, "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        row = json.loads(res.stdout)[0]
        self.assertEqual(row["path"], "src/pricing.py")
        self.assertEqual(row["risk"], "high")
        self.assertEqual(row["fan_in"], 5)
        self.assertEqual(row["tests_touching"], ["tests/test_pricing.py"])
        self.assertEqual(row["fix_rate"], 1.0)

    def test_js_dependents(self) -> None:
        self.build(users=0)
        res = self.run_script(IMPACT, "--files", "web/lib/total.ts", "--json")
        row = json.loads(res.stdout)[0]
        self.assertEqual(row["dependents"], ["web/cart.ts"])
        self.assertIn("total", row["callers"])

    def test_from_plan_before_any_change(self) -> None:
        self.build(users=2)
        self.write("docs/changes/eng-1/plan.md", PLAN.format(impact=""))
        res = self.run_script(IMPACT, "--from-plan")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("| src/pricing.py | mid | 2 |", res.stdout)
        self.assertIn("imported by src/user0.py", res.stdout)

    def test_check_requires_high_risk_files_in_impact(self) -> None:
        self.build(users=5)
        self.write("src/pricing.py", "def price(x):\n    return round(x, 2)\n")
        self.write("docs/changes/eng-1/plan.md", PLAN.format(impact=""))
        res = self.run_script(IMPACT, "--check")
        self.assertEqual(res.returncode, 1)
        self.assertIn("high-risk src/pricing.py", res.stdout)
        self.write("docs/changes/eng-1/plan.md", PLAN.format(
            impact="- src/pricing.py — callers in src/user*.py covered by tests/test_pricing.py::test_rounding"))
        res = self.run_script(IMPACT, "--check")
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


if __name__ == "__main__":
    unittest.main()
