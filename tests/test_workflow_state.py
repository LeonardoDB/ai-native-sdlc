"""Tests for scripts/workflow_state.py (F1 — deterministic workflow state)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills" / "ai-native-sdlc" / "scripts" / "workflow_state.py"
)
GATE_LEDGER = (
    Path(__file__).resolve().parent.parent
    / "skills" / "ai-native-sdlc" / "scripts" / "gate_ledger.py"
)


GRAPH = """\
# Test graph
version: 1

nodes:
  intent:
    stage: plan
    artifact: intent/intent.md
    gate: product_owner_accept
    status: in_review
    done_status: accepted
  spec:
    stage: design
    artifact: spec.md
    gate: product_owner_approve
    status: not_started
    done_status: approved

edges:
  - { from: intent, to: spec, trigger: acceptance }
"""


def make_repo() -> Path:
    td = tempfile.mkdtemp()
    return Path(td)


def write_graph(root: Path, status: str = "in_review", graph_text: str | None = None) -> Path:
    text = graph_text or GRAPH.replace("status: in_review", f"status: {status}", 1)
    graph = root / "workflow-graph.yaml"
    graph.write_text(text, encoding="utf-8")
    return graph


def record(root: Path, gate: str = "product_owner_accept", record_id: str = "r-1") -> None:
    subprocess.run(
        [
            sys.executable,
            str(GATE_LEDGER),
            "--ledger",
            str(root / "gates" / "ledger.jsonl"),
            "record",
            "--gate",
            gate,
            "--artifact",
            "intent.md",
            "--commit",
            "abc123",
            "--approver",
            "Ada",
            "--evidence",
            "review-1",
            "--id",
            record_id,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=root,
        capture_output=True,
        text=True,
    )


def graph_text(root: Path) -> str:
    return (root / "workflow-graph.yaml").read_text(encoding="utf-8")


class WorkflowStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = make_repo()
        self.addCleanup(lambda: os.system(f"rm -rf {self.root}"))

    def test_advance_closes_node_with_matching_record(self) -> None:
        write_graph(self.root)
        record(self.root)
        res = run(
            self.root,
            "advance",
            "--node",
            "intent",
            "--record",
            "r-1",
        )
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        self.assertIn("status: accepted", graph_text(self.root))

    def test_advance_refuses_record_for_wrong_gate(self) -> None:
        write_graph(self.root)
        record(self.root, gate="release_authorization", record_id="r-other")
        before = graph_text(self.root)
        res = run(
            self.root,
            "advance",
            "--node",
            "intent",
            "--record",
            "r-other",
        )
        self.assertEqual(res.returncode, 1)
        self.assertEqual(graph_text(self.root), before)
        self.assertIn("gate", res.stderr)

    def test_advance_refuses_node_not_in_review_or_pending(self) -> None:
        write_graph(self.root, status="in_progress")
        record(self.root)
        before = graph_text(self.root)
        res = run(
            self.root,
            "advance",
            "--node",
            "intent",
            "--record",
            "r-1",
        )
        self.assertEqual(res.returncode, 1)
        self.assertEqual(graph_text(self.root), before)
        self.assertIn("in_review", res.stderr)

    def test_advance_requires_record(self) -> None:
        write_graph(self.root)
        res = run(
            self.root,
            "advance",
            "--node",
            "intent",
            "--record",
            "missing",
        )
        self.assertEqual(res.returncode, 1)

    def test_advance_require_committed_rejects_uncommitted_ledger(self) -> None:
        write_graph(self.root)
        record(self.root)
        res = run(
            self.root,
            "advance",
            "--node",
            "intent",
            "--record",
            "r-1",
            "--require-committed",
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn("committed", res.stderr)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(
            ["git", "-C", str(self.root), "add", "-A"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "-c", "user.email=test@example.com",
             "-c", "user.name=Test", "commit", "-qm", "graph and ledger"],
            check=True,
            capture_output=True,
        )
        res = run(
            self.root,
            "advance",
            "--node",
            "intent",
            "--record",
            "r-1",
            "--require-committed",
        )
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_advance_rejects_broken_hash_chain(self) -> None:
        write_graph(self.root)
        record(self.root, record_id="r-1")
        ledger = self.root / "gates" / "ledger.jsonl"
        rec = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
        rec["approver"] = "Mallory"
        ledger.write_text(json.dumps(rec, sort_keys=True) + "\n", encoding="utf-8")
        res = run(
            self.root,
            "advance",
            "--node",
            "intent",
            "--record",
            "r-1",
        )
        self.assertEqual(res.returncode, 1)
        self.assertIn("hash", res.stderr.lower())

    def test_check_flags_done_node_without_record(self) -> None:
        write_graph(self.root, status="accepted")
        res = run(self.root, "check")
        self.assertEqual(res.returncode, 1)
        self.assertIn("product_owner_accept", res.stdout + res.stderr)
        record(self.root)
        res = run(self.root, "check")
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)

    def test_check_flags_unknown_status_and_self_edge(self) -> None:
        write_graph(self.root, status="bogus")
        res = run(self.root, "check")
        self.assertEqual(res.returncode, 1)

        text = GRAPH.replace(
            "  - { from: intent, to: spec, trigger: acceptance }",
            "  - { from: intent, to: intent, trigger: acceptance }",
        )
        write_graph(self.root, graph_text=text)
        res = run(self.root, "check")
        self.assertEqual(res.returncode, 1)
        self.assertIn("self", res.stdout + res.stderr)

    def test_status_reports_drift_warnings_and_json(self) -> None:
        write_graph(self.root, status="not_started")
        (self.root / "intent").mkdir()
        (self.root / "intent" / "intent.md").write_text("artifact", encoding="utf-8")
        res = run(self.root, "status", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        nodes = {n["node"]: n for n in data["nodes"]}
        self.assertEqual(nodes["intent"]["status"], "not_started")
        self.assertTrue(
            any("not_started" in w or "artifact" in w for w in nodes["intent"]["warnings"])
        )

        text_res = run(self.root, "status")
        self.assertEqual(text_res.returncode, 0, text_res.stderr)
        self.assertIn("intent", text_res.stdout)
        self.assertIn("spec", text_res.stdout)

    def test_status_warns_when_record_arrives_before_node_is_ready(self) -> None:
        write_graph(self.root, status="not_started")
        record(self.root)
        res = run(self.root, "status", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout)
        intent = next(n for n in data["nodes"] if n["node"] == "intent")
        self.assertTrue(any("recorded" in w.lower() for w in intent["warnings"]))

    def test_failed_advance_leaves_graph_unchanged(self) -> None:
        write_graph(self.root)
        record(self.root, gate="release_authorization", record_id="r-wrong")
        before = graph_text(self.root)
        res = run(
            self.root,
            "advance",
            "--node",
            "intent",
            "--record",
            "r-wrong",
        )
        self.assertEqual(res.returncode, 1)
        self.assertEqual(graph_text(self.root), before)


if __name__ == "__main__":
    unittest.main()
