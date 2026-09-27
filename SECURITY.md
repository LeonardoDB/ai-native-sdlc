# Security

This repository ships guardrails other teams rely on: `check_plan_sync.py`
(the plan-mode check), the rule that the agent stops at the opened MR/PR and
never merges or deploys, and the rule that it never edits tracker tasks. Bugs
in them matter more than bugs in ordinary code.

## Reporting a vulnerability

Please report bypasses and script issues privately before opening a public
issue:

- Open a private advisory via GitHub's security tab, **or**
- Email the maintainers (see the repository metadata / plugin author) with the
  subject `[ai-native-sdlc security]`.

Include: the affected file and version, a reproduction, and the impact. Do
not include real credentials or production data.

## What we consider security-relevant

- Bypasses of `scripts/check_plan_sync.py` (implementation that passes without
  an approved plan covering it), `scripts/check_tdd.py` (a test that passes
  without the change reported as red), or `scripts/check_diff_hygiene.py`.
- `check_tdd.py` runs the Proof commands written in the repo's own plan.md, in
  the repo root, and temporarily removes implementation files (git stash, or a
  checkout of `--base`) — anything that loses work or leaves the tree changed
  after a run is a bug.
- Bypasses of `hooks/gate.py`: a merge, a push to the default branch, a
  `--no-verify`, a bare force-push, or a publish with failing checks that the
  gate lets through.
- Skill instructions that lead the agent to merge, deploy, push without the
  user's go-ahead, or write to a tracker task without confirmation.
- Command or path injection in the scripts beyond the Proof commands a
  plan.md explicitly declares.

## Non-goals (out of scope)

- Vulnerabilities in third-party tools the workflow merely *uses* (tracker
  CLIs and MCP connectors, forges).
- Misconfiguration by adopters who weaken the defaults on purpose.
