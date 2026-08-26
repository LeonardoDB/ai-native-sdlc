# Changelog

All notable changes to this repository are documented here. Versions are
semver; keep `plugin.json` and the `version` field in SKILL.md in sync
(`scripts/quick_validate.py` enforces this).

## [Unreleased]

### Added

- `scripts/gate_ledger.py` — hash-chained, version-controlled approval ledger:
  every gate decision is a tamper-evident record (`record`/`list`/`verify`);
  `verify --require-committed` and `--graph … --require-gates` completeness
  checks; the release gate now accepts `RELEASE_APPROVAL=ledger:<id>` and
  verifies the record before allowing a deploy.
- `assets/gates-README.md` — gate ledger usage (scaffolded as `gates/README.md`).
- `tests/test_gate_ledger.py` — chain integrity, tamper detection, expiry,
  wrong-decision, require-committed, and graph-completeness cases; ledger
  integration cases in `tests/test_gate.sh` (uncommitted/valid/unknown/
  tampered).
- `scripts/quick_validate.py` — self-contained skill/plugin validator; the
  AGENTS.md validation step now has a real implementation.
- `scripts/run_evals.py` — eval-suite runner for Phase 4 (local + CI) with the
  canonical JSON eval format and `--min-pass-rate` gating.
- `scripts/detect_bands.py` — deterministic control-band detector reference
  implementation (rolling-30d mean/σ, Western Electric rules, drift rule),
  unit-tested; consumes `bands.yaml`.
- Templates: `assets/incident.md`, `assets/runbooks/rollback-deploy.md`,
  `assets/runbooks/README.md`, `assets/PULL_REQUEST_TEMPLATE.md`,
  `assets/evals.example.json`, `assets/evals-README.md`,
  `assets/workflow-graph.yaml` (project graph state), `assets/.gitignore`.
- Tests: `tests/test_gate.sh`, `tests/test_init.sh`,
  `tests/test_detect_bands.py`, `tests/test_run_evals.py`.
- `.github/workflows/self-check.yml` — CI for the repo itself (shell syntax,
  unit tests, integration tests, skill/plugin validation).
- `SECURITY.md`; `version` field in SKILL.md frontmatter; compliance matrix in
  SKILL.md mapping each hard rule to its enforcement layer.

### Changed

- `assets/production-gate.sh` — replaced naive `deploy`+`production` word
  matching with deploy-action patterns (`DEPLOY_PATTERNS`), production-context
  matching, and a read-only allowlist (`READ_ONLY_PATTERNS`). Previously the
  gate was both bypassable (`terraform apply -target=module.production`,
  `helm upgrade prod-app`) and over-blocking (`cat docs/production-deploy.md`).
  Added `RELEASE_APPROVAL_EXPIRY` (ISO-8601 or epoch, fail-closed) and
  jq-independent JSON parsing.
- `scripts/init_workflow.py` — scaffolds `workflow-graph.yaml`, `.gitignore`,
  and `evals/README.md`; adds `--dry-run`, `--git`, and `--name` validation;
  fixed the codex-mode existence check (CLAUDE.md vs AGENTS.md).
- `assets/agent-evals.yml.example` — now calls `run_evals.py`; previously it
  referenced a `check.sh` that the repo never shipped.
- `README.md`, `AGENTS.md` — validation instructions point at real artifacts;
  the loop table now has a single source of truth (SKILL.md).

## [0.1.0] — 2026-08-21

Initial release: skill + plugin bundle implementing the AI-native SDLC loop
(Plan → Design → Build → Test → Deploy → Maintain) with versioned artifacts
and human approval gates.
