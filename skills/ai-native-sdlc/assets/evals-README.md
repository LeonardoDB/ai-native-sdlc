# Evals (Phase 4 — Test)

Each eval is **one JSON file** in this directory (`evals/*.json`). An eval is a
real task from recent work, its prompt, and machine-checkable pass conditions.

Run the suite locally:

```bash
python3 scripts/run_evals.py evals/ --min-pass-rate 0.9
```

Run it in CI on every change to CLAUDE.md, skills, or hooks — that
configuration steers the agent and deserves the same regression testing as
code (see `assets/agent-evals.yml.example` in the skill). Add an eval after
every production incident: the incident becomes a permanent regression test.

## Format

```json
{
  "name": "short label",
  "prompt": "exactly what the agent receives",
  "agent": { "cli": "claude -p" },
  "checks": [
    { "run": "command", "expect_exit": 0, "contains": "expected output substring" },
    "plain command that must exit 0"
  ]
}
```

- `agent.cli` is optional; when set, the prompt is first run through that CLI
  (override with the `AGENT_CLI` env var; `--no-agent` skips it).
- `checks` are deterministic shell commands run in the repo; a check passes on
  `expect_exit` (default 0) plus every `contains` substring.
- Empty or missing `checks` makes the eval fail: an eval without
  machine-checkable proof is not an eval.

See `assets/evals.example.json` in the skill for a filled-in example, and
`evals/example.md` for the markdown reference form.
