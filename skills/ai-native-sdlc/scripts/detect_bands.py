#!/usr/bin/env python3
"""Deterministic control-band detection for the Maintain phase.

Reads a metrics feed and bands.yaml, applies rolling-window mean/std with
Western Electric-style rules, and emits incident records for breached bands.
Detection is deterministic and unit-tested - no model involved.

Usage:
    python3 detect_bands.py --metrics metrics.csv [--bands bands.yaml]
           [--window-days 30] [--drift-run 8] [--output incidents.jsonl]
           [--fail-on 3sigma]

metrics.csv columns: ts,metric,value   (ts = ISO-8601 or epoch seconds)

bands.yaml is the bands asset format:
    metrics:
      <metric>:
        baseline: rolling_30d
        rules: western_electric
        tiers:
          1sigma: { action: log }
          2sigma: { action: diagnose, tools: "Read,Grep" }
          3sigma: { action: propose, routes: ["pull_request", "runbook:rollback-deploy"] }

Tier rules (per metric, on the latest point vs the rolling window):
  1sigma: value beyond mean +- 1*std          -> log
  2sigma: value beyond mean +- 2*std, or a run of >= --drift-run consecutive
          points on the same side beyond 1*std -> diagnose
  3sigma: value beyond mean +- 3*std           -> propose (act through gated routes)

Exit codes: 0 = ok, 1 = error, 2 = a band at or above --fail-on was breached.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml as _yaml  # type: ignore

    def _load_yaml(path: Path):
        with open(path, encoding="utf-8") as fh:
            return _yaml.safe_load(fh) or {}

except ImportError:  # pragma: no cover - fallback parser is used in tests anyway
    _yaml = None  # type: ignore

    def _load_yaml(path: Path):
        return parse_simple_yaml(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Minimal YAML-subset parser (maps, scalars, inline flow maps/lists).
# Used when PyYAML is unavailable; unit-tested against the bands asset.
# --------------------------------------------------------------------------

def _split_top(s: str) -> list[str]:
    """Split on commas outside quotes/braces (flow maps and lists)."""
    parts, depth, cur, in_q = [], 0, "", None
    for ch in s:
        if in_q:
            cur += ch
            if ch == in_q:
                in_q = None
        elif ch in "\"'":
            in_q, cur = ch, cur + ch
        elif ch in "{[":
            depth += 1
            cur += ch
        elif ch in "}]":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def _parse_scalar(s: str):
    s = s.strip()
    if not s:
        return None
    if s.startswith("{") and s.endswith("}"):
        out = {}
        for part in _split_top(s[1:-1]):
            k, _, v = part.partition(":")
            out[k.strip().strip('"\'')] = _parse_scalar(v.strip())
        return out
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [] if not inner else [_parse_scalar(x.strip()) for x in _split_top(inner)]
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s in ("null", "None"):
        return None
    if s.lstrip("-").isdigit():
        return int(s)
    return s


def parse_simple_yaml(text: str) -> dict:
    """Parse the YAML subset used by bands.yaml and workflow-graph.yaml."""
    lines: list[str] = []
    for raw in text.splitlines():
        s = raw.rstrip()
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        lines.append(s)
    root: dict = {}
    stack: list[tuple[int, str, dict, object]] = []  # (indent, key, parent, node)
    for line in lines:
        indent = len(line) - len(line.lstrip())
        content = line.strip()
        if content.startswith("- "):
            while stack and stack[-1][0] >= indent:
                stack.pop()
            if not stack:
                raise ValueError("top-level list not supported")
            _, key, parent, node = stack[-1]
            if not isinstance(node, list):
                node = []
                parent[key] = node
                stack[-1] = (stack[-1][0], key, parent, node)
            node.append(_parse_scalar(content[2:].strip()))
            continue
        key, _, value = content.partition(":")
        key = key.strip().strip('"\'')
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent: dict = stack[-1][3] if stack else root
        if not value.strip():
            node: dict = {}
            parent[key] = node
            stack.append((indent, key, parent, node))
        else:
            parent[key] = _parse_scalar(value.strip())
    return root


# --------------------------------------------------------------------------
# Metrics loading
# --------------------------------------------------------------------------

def _to_epoch(ts) -> float | None:
    if isinstance(ts, (int, float)):
        return float(ts)
    s = str(ts).strip()
    try:
        return float(s)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def load_metrics(path: str) -> dict[str, list[tuple[float, float]]]:
    rows: list[dict] = []
    if path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    else:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        rows = data.get("metrics", data) if isinstance(data, dict) else data

    out: dict[str, list[tuple[float, float]]] = {}
    for row in rows:
        metric = row.get("metric") or row.get("name")
        ts = _to_epoch(row.get("ts"))
        if not metric or ts is None:
            continue
        try:
            value = float(row["value"])
        except (TypeError, ValueError):
            continue
        out.setdefault(metric, []).append((ts, value))
    for series in out.values():
        series.sort(key=lambda p: p[0])
    return out


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

DEFAULT_BANDS = {
    "metrics": {
        "ci_test_failure_rate": {"tiers": {
            "1sigma": {"action": "log"},
            "2sigma": {"action": "diagnose", "tools": "Read,Grep,Bash(gh run view *)"},
            "3sigma": {"action": "propose", "routes": ["pull_request", "runbook:rollback-deploy"]},
        }},
        "post_deploy_5xx_rate": {"tiers": {
            "1sigma": {"action": "log"},
            "2sigma": {"action": "diagnose", "tools": "Read,Grep,Bash(gh run view *)"},
            "3sigma": {"action": "propose", "routes": ["pull_request", "runbook:rollback-deploy"]},
        }},
        "pr_cycle_time": {"tiers": {
            "1sigma": {"action": "log"},
            "2sigma": {"action": "diagnose", "tools": "Read,Grep,Bash(gh run view *)"},
            "3sigma": {"action": "propose", "routes": ["pull_request", "runbook:rollback-deploy"]},
        }},
    }
}


def _stats(values: list[float]) -> tuple[float, float]:
    n = len(values)
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return mean, math.sqrt(var)


def detect(
    metric: str,
    series: list[tuple[float, float]],
    config: dict,
    window_days: int = 30,
    drift_run: int = 8,
) -> list[dict]:
    """Return incident records for the metric's series, if any band is breached."""
    if len(series) < 3:
        return []
    max_ts = series[-1][0]
    cutoff = max_ts - window_days * 86400
    window = [p for p in series if p[0] >= cutoff]
    if len(window) < 3:
        window = series
    values = [p[1] for p in window]
    mean, std = _stats(values)
    latest_ts, latest = window[-1]

    if std == 0:
        sigma = float("inf") if latest != mean else 0.0
    else:
        sigma = (latest - mean) / std

    tier: str | None = None
    if sigma == float("inf") or sigma > 3:
        tier = "3sigma"
    elif sigma > 2:
        tier = "2sigma"
    elif sigma > 1:
        tier = "1sigma"

    # Drift: a run of consecutive points on the same side beyond 1*std
    # (Western Electric rule 4, simplified) -> escalate to diagnose.
    if std > 0:
        run = 0
        for _, v in reversed(window):
            if v > mean + std or v < mean - std:
                run += 1
            else:
                break
        if run >= drift_run and tier in (None, "1sigma"):
            tier = "2sigma"

    if tier is None:
        return []

    tiers_cfg = (config.get("tiers") or {}) if isinstance(config, dict) else {}
    entry = tiers_cfg.get(tier, {}) if isinstance(tiers_cfg, dict) else {}
    action = entry.get("action", "log") if isinstance(entry, dict) else "log"
    routes = entry.get("routes") if isinstance(entry, dict) else None

    return [{
        "ts": latest_ts,
        "metric": metric,
        "tier": tier,
        "action": action,
        "sigma": None if sigma == float("inf") else round(sigma, 3),
        "value": latest,
        "mean": round(mean, 3),
        "std": round(std, 3),
        "window_points": len(window),
        "routes": routes,
    }]


def load_bands(path: str | None) -> dict:
    if path:
        data = _load_yaml(Path(path))
        return data.get("metrics", data) if isinstance(data, dict) else {}
    return DEFAULT_BANDS["metrics"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", required=True, help="metrics.csv or metrics.json")
    parser.add_argument("--bands", default=None, help="bands.yaml (default: built-in bands)")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--drift-run", type=int, default=8)
    parser.add_argument("--output", default=None, help="write incidents JSONL to this file")
    parser.add_argument("--fail-on", choices=["1sigma", "2sigma", "3sigma"], default=None)
    args = parser.parse_args(argv)

    bands = load_bands(args.bands)
    metrics = load_metrics(args.metrics)
    incidents: list[dict] = []
    for name, series in sorted(metrics.items()):
        incidents.extend(detect(name, series, bands.get(name, {}), args.window_days, args.drift_run))

    text = "\n".join(json.dumps(i) for i in incidents)
    if args.output:
        Path(args.output).write_text(text + ("\n" if incidents else ""), encoding="utf-8")
    else:
        print(text)

    if args.fail_on and any(i["tier"] == args.fail_on for i in incidents):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
