#!/usr/bin/env python3
"""Unit tests for scripts/detect_bands.py."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills/ai-native-sdlc/scripts"))
import detect_bands  # noqa: E402


class ParseTests(unittest.TestCase):
    def test_parse_actual_bands_asset(self):
        asset = Path(__file__).resolve().parent.parent / "skills/ai-native-sdlc/assets/bands.yaml"
        cfg = detect_bands.parse_simple_yaml(asset.read_text(encoding="utf-8"))
        self.assertIn("ci_test_failure_rate", cfg["metrics"])
        tiers = cfg["metrics"]["ci_test_failure_rate"]["tiers"]
        self.assertEqual(tiers["1sigma"]["action"], "log")
        self.assertEqual(tiers["2sigma"]["action"], "diagnose")
        self.assertEqual(tiers["3sigma"]["action"], "propose")
        self.assertIn("runbook:rollback-deploy", tiers["3sigma"]["routes"])

    def test_parse_flow_and_inline_lists(self):
        cfg = detect_bands.parse_simple_yaml(
            "a:\n  b: { x: 1, y: two }\n  c: [1, two, \"three\"]\n"
        )
        self.assertEqual(cfg["a"]["b"], {"x": 1, "y": "two"})
        self.assertEqual(cfg["a"]["c"], [1, "two", "three"])


class DetectTests(unittest.TestCase):
    def test_flat_series_no_signal(self):
        series = [(float(i), 5.0) for i in range(20)]
        self.assertEqual(detect_bands.detect("m", series, {}), [])

    def test_big_spike_is_3sigma(self):
        series = [(float(i), 0.0) for i in range(10)] + [(10.0, 100.0)]
        inc = detect_bands.detect("m", series, {"tiers": {"3sigma": {"action": "propose", "routes": ["pull_request"]}}})
        self.assertEqual(len(inc), 1)
        self.assertEqual(inc[0]["tier"], "3sigma")
        self.assertEqual(inc[0]["action"], "propose")

    def test_moderate_move_is_1sigma_log(self):
        series = [(float(i), 0.0 if i % 2 == 0 else 2.0) for i in range(9)] + [(9.0, 2.5)]
        inc = detect_bands.detect("m", series, {"tiers": {"1sigma": {"action": "log"}}})
        self.assertEqual(len(inc), 1)
        self.assertEqual(inc[0]["tier"], "1sigma")
        self.assertEqual(inc[0]["action"], "log")

    def test_drift_escalates_to_diagnose(self):
        # Last 8 points all sit beyond mean+1*std: drift rule escalates 1sigma -> 2sigma.
        series = [(float(i), 0.0) for i in range(12)] + [(float(i), 0.1) for i in range(12, 20)]
        inc = detect_bands.detect(
            "m", series, {"tiers": {"1sigma": {"action": "log"}, "2sigma": {"action": "diagnose"}}}
        )
        self.assertEqual(len(inc), 1)
        self.assertEqual(inc[0]["tier"], "2sigma")
        self.assertEqual(inc[0]["action"], "diagnose")

    def test_window_filters_old_points(self):
        now = time.time()
        old = [(now - 40 * 86400 + i, 100.0) for i in range(10)]
        recent = [(now - 86400 + i, 10.0) for i in range(10)]
        inc = detect_bands.detect("m", old + recent, {}, window_days=30)
        self.assertEqual(inc, [])  # window = flat 10s; the 100s are outside the window

    def test_window_changes_signal(self):
        now = time.time()
        old = [(now - 40 * 86400 + i, 0.0) for i in range(10)]
        recent = [(now - 86400 + i, 0.0) for i in range(19)] + [(now - 1, 100.0)]
        inc = detect_bands.detect("m", old + recent, {"tiers": {"3sigma": {"action": "propose"}}}, window_days=30)
        self.assertEqual(len(inc), 1)
        self.assertEqual(inc[0]["tier"], "3sigma")
        self.assertEqual(inc[0]["window_points"], 20)  # old 100s excluded


class CliTests(unittest.TestCase):
    def test_end_to_end_with_fail_on(self):
        now = time.time()
        with tempfile.TemporaryDirectory() as td:
            metrics = os.path.join(td, "metrics.csv")
            with open(metrics, "w", encoding="utf-8") as fh:
                fh.write("ts,metric,value\n")
                for i in range(10):
                    fh.write(f"{now - 86400 + i},m,0.0\n")
                fh.write(f"{now},m,100.0\n")
            out = os.path.join(td, "incidents.jsonl")
            rc = detect_bands.main(["--metrics", metrics, "--output", out, "--fail-on", "3sigma"])
            self.assertEqual(rc, 2)
            with open(out, encoding="utf-8") as fh:
                incidents = [json.loads(line) for line in fh if line.strip()]
            self.assertEqual(len(incidents), 1)
            self.assertEqual(incidents[0]["tier"], "3sigma")


if __name__ == "__main__":
    unittest.main()
