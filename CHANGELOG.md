# Changelog

All notable changes to this repository are documented here. Versions are
semver; keep `plugin.json` and the `version` field in SKILL.md in sync
(`scripts/quick_validate.py` enforces this).

## [Unreleased]

### Removed

- Codex support: the `.codex-plugin/` manifest, `agents/openai.yaml`,
  `init_workflow.py --framework` (it always writes CLAUDE.md), and the Codex
  install and framework-mapping docs. The bundle targets Claude Code only.

### Added

- Models per role: a **builder** subagent (`references/agents/builder.md`)
  implements each slice after the shape is approved, on a cheaper model;
  the session — on the strongest model — keeps the spec, the plan, the shape,
  and the review filter. CLAUDE.md's optional `## Models` sets each role's
  model (defaults: explorer and builder `sonnet`, architect and reviewer
  `inherit`; `builder: inherit` builds in the session).
- Shape step in Build (hard rule 9): after the plan is approved, the types
  and signatures are written as stubs and judged by a new **architect**
  subagent (`references/agents/architect.md`) in a fresh context, round by
  round, until it approves — before any test or code. plan.md's `## Types
  first` becomes `## Shape`; `check_diff_hygiene.py` fails on an open
  architect finding or a missing `Verdict: approved`; `tracker_link.py`
  reports `next: shape`; `metrics.py` counts `shape_rounds`.
- Eval `09-kb-recall`: an ADR the code does not reveal (money is Decimal, after an incident) must be read, cited in the spec, and followed.
- `check_diff_hygiene.py` fails while a `- [ ]` entry is left untriaged under
  plan.md's `## Learnings`; `metrics.py` reports learnings promoted and
  dropped per task.
- Knowledge stores (`references/knowledge.md`): CLAUDE.md's
  `## Knowledge base` now declares stores by name, purpose, transport (repo
  path, MCP server, CLI/API), and who may write, plus conventions and store
  skills. Recall runs in Design, Build, debugging, Review, and MR feedback,
  with every hit cited. Capture goes through a per-task `## Learnings`
  section in plan.md (no shared ledger to conflict across branches), triaged
  at the end of Review under a six-point quality gate: repo stores are
  written into the change and reviewed in the MR; external stores are
  written only inside the delivery go-ahead.
- Evals for `claude plugin eval` (`evals/`): eight cases — the full loop to
  an MR, stopping for plan approval, rejecting a board link, stopping on a
  dirty tree, listing an existing test change, one MR feedback round, a bug
  fixed from its root cause, and a plain question that must not start the
  workflow. A shared offline fixture (`evals/_fixtures/shop.sh`) builds a
  Python repo with a GitLab origin that pushes to a local bare repo and a
  `glab` stand-in that logs every call, so most graders are deterministic
  (files, tracker log, the `check_tdd` line in the trace). First runs:
  `03-board-link-rejected` and `08-neg-explain` 1.00 on haiku.
- Regression guards in Proof: an acceptance criterion that keeps behavior
  the code already has is marked `regression:` and `check_tdd.py` checks it
  green only — it cannot fail without the change, and flagging it made
  nearly every real task fail. The reviewer checks the mark is not hiding a
  new behavior.
- Claude Code plugin: `.claude-plugin/plugin.json` and `marketplace.json`
  (the repo root is the plugin), with `hooks/hooks.json` wiring the gate on
  PreToolUse Bash. Install with `claude plugin marketplace add
  LeonardoDB/ai-native-sdlc` and `claude plugin install
  ai-native-sdlc@ai-native-sdlc`. `quick_validate.py` checks both manifests
  against SKILL.md; the README recommends the plugin and a symlink for the
  skill-only install.
- MR/PR feedback: `tracker_link.py` accepts MR/PR links (`kind:
  merge_request`, ref `group/project!12` or `owner/repo#12`), and
  `references/feedback.md` runs one round — read every thread, check out the
  source branch, triage (question, change in scope, out of scope,
  disagreement), fix test-first, re-run the checks, and push and reply on one
  go-ahead. Never merges.
- Bug tasks: `references/debugging.md` — reproduce as a failing test,
  evidence and `git bisect run`, one hypothesis at a time, the root cause in
  the plan before the fix, siblings as follow-ups.
- `scripts/metrics.py`: rework metrics from what each task already records
  in `docs/changes/<task>/` and git — spec rework after the plan, plan edits,
  review rounds (`### Round <n>`), deviations, test changes, accepted
  surviving mutants, lead time — per task and in aggregate, across repos;
  `--forge` adds MR/PR comments and days to merge via `gh` or `glab`.
- `hooks/gate.py`: Claude Code PreToolUse hook enforcing the red lines —
  blocks `glab mr merge`/`gh pr merge`, pushes to the default branch,
  `--no-verify`/`--no-gpg-sign`, and force-pushes without a lease; lets a task
  branch be pushed or its MR/PR opened only on a clean tree with
  `check_plan_sync`, `check_tdd`, `check_diff_hygiene`, and
  `impact_map --check` passing (`SDLC_GATE_MUTATIONS=1` adds mutations).
  No Stop hook, by design. Tested in `tests/test_gate.py`.
- `scripts/impact_map.py`: per changed file, the files that import it
  (Python and JS/TS), the files using the symbols the change adds or edits,
  the last year's commits and fix rate, and a high/mid/low risk. Run with
  `--from-plan` before the change to fill plan.md's new `## Impact`, and with
  `--check` in Review to fail a high-risk file the plan does not name.
  Searches in Python over tracked files, so results match on every platform.
- `scripts/check_mutations.py`: mutation check on the lines a change adds
  (implementation only) — flipped comparisons, swapped and/or, off-by-one
  constants, inverted booleans, `+`/`-` — run one at a time against the
  plan's Proof commands, with every file restored afterwards. A surviving
  mutant fails unless plan.md lists it under `## Surviving mutants` with the
  reason. Working tree or `--base` (CI); `--max` caps the run. Scaffolded and
  tested (`tests/test_check_mutations.py`).
- Test-first, typed Build: `scripts/check_tdd.py` proves every acceptance
  criterion maps to a Proof command (or manual evidence) and that each
  command passes with the change and fails with the implementation removed
  (git stash in the working tree, or `--base` in CI) — a test that passes
  without the change fails the check. `scripts/check_diff_hygiene.py` fails
  added type/lint suppressions (`any`, `@ts-ignore`, `# type: ignore`,
  `eslint-disable`, …) and skipped or focused tests without a `reason:`, and
  rewritten or deleted existing tests not listed under plan.md's Test changes.
  Both are scaffolded and tested (`tests/test_check_tdd.py`).
- plan.md: acceptance criteria (light path), Types first (declarations with
  stub bodies, type-checked, reviewed, then frozen), vertical-slice order of
  work, Proof (AC → command), Test changes, Deviations, test-suite baseline,
  and a Build log with red evidence. spec.md gains numbered acceptance
  criteria. CLAUDE.md gains a Typecheck command and an optional
  `## Code tooling` section (LSP, library docs). The reviewer brief checks
  test honesty (tautologies, mocks of own code, surviving mutations, red for
  the wrong reason) and types (closed sets, invalid states, frozen
  signatures).
- Subagents: `references/agents/explorer.md` (Design — read-only, `file:line`
  map and ranked essential files, knowledge-base recall) and
  `references/agents/reviewer.md` (Review — fresh context, three lenses,
  every finding scored by confidence and severity). The coordinator filters
  (keep ≥ 80, check high-severity lower ones), records rejections in plan.md
  `## Review`, walks the task's acceptance criteria with evidence, and stops
  after two review rounds.
- Workspace before code: branch `<type>/<slug>-<summary>` off the fetched
  default branch on the user's go-ahead, stop on a dirty tree, worktree only
  on request (`.worktrees/` ignored by the scaffold).
- Resuming: `tracker_link.py` reports the git state (branch, default branch,
  dirty), `on_task_branch`, and the task `state` (`next`: design,
  approve-spec, plan, approve-plan, implement) read from `docs/changes/<task>/`.
- Light path: localized changes skip the spec; plan.md is the one approval.
  plan.md gains `Path` and `## Review`; the MR/PR template gains acceptance
  criteria and the reviewer lenses.

### Removed

- Everything outside the task → MR/PR loop, and what did not fit it: the
  release gate (`production-gate.sh`, hook and managed-settings examples,
  `tests/test_gate.sh`), evals (`run_evals.py` and its assets), monitoring
  (`bands.yaml`, `detect_bands.py`, `incident.md`, `runbooks/`), the agent org
  (`init_org.py`, `org_status.py`, `intake.py`, `sync_issues.py`,
  `assets/org/`, `references/org.md`), the gate ledger and graph state
  (`gate_ledger.py`, `workflow_state.py`, `workflow-graph*.yaml`,
  `gates-README.md`, `references/graph.md`), the expense-tracker example, and
  the six-phase banner. One pipeline state per repo could not track parallel
  tasks, and the board, the spec/plan approvals, and the MR/PR already record
  the gates.

### Changed

- Per-task artifacts: spec.md and plan.md live in `docs/changes/<task>/`, so
  parallel branches never collide. `tracker_link.py` outputs the task `slug`
  and `change_dir`; `check_plan_sync.py` finds the plan the diff touches (or,
  in hook mode, the folder named by the branch), no longer depends on the
  ledger, and treats `.github/`/`.gitlab/` as process paths (the old
  `lstrip("./")` stripped their leading dot). `init_workflow.py` scaffolds only
  CLAUDE.md/AGENTS.md, REVIEW.md, `.gitignore`, and `check_plan_sync.py`
  (`--name` removed). SKILL.md, playbook, adoption, trackers, README, AGENTS,
  SECURITY, and CI describe the four-phase loop.

### Added

- Knowledge base in Design: the CLAUDE.md template gains an optional
  `## Knowledge base` section (pointers — repo path or MCP store — never the
  knowledge itself). Design searches it before writing `spec.md`, which now
  lists the knowledge used; conflicts with the task become open questions.
- Intent from the tracker: `scripts/tracker_link.py parse <link>` resolves a
  Linear, GitLab, or GitHub task link to its system and native ref and checks
  it against the current repo's `origin` — no config (GitLab, self-hosted
  included, is recognized by its `/-/` link shape), offline, deterministic;
  board, epic, project, and MR links exit 1. Flow and rules in
  `references/trackers.md`; optional `## Tracker` section in the CLAUDE.md
  template for per-project exceptions; tests in `tests/test_tracker_link.py`.
- Deterministic workflow state runtime (`scripts/workflow_state.py`): `status`
  reports pipeline state and drift warnings, `advance` closes a graph node only
  through a matching chain-verified ledger record, and `check` validates graph
  schema/ledger consistency (`--strict` also rejects uncommitted
  advance-ready records). Scaffolded by `init_workflow.py`; `done_status` added
  to graph templates and the expense-tracker example.
- Deterministic plan-sync enforcement (`scripts/check_plan_sync.py`): PR/CI
  (`--base/--head`) and pre-commit (`--hook`) modes verify implementation
  changes against an approved `plan.md` "Files that change" manifest, with
  glob matching, process-file exclusions, and optional ledger-gate
  verification delegated to `gate_ledger.py`. Scaffolded by `init_workflow.py`.
- Agent-org operations tooling: `scripts/org_status.py` (validated busy/idle
  and review-queue transitions: assign, submit, escalate) and
  `scripts/intake.py` (form/email record ingestion and queue listing).
  Scaffolded by `init_org.py`.
- Autonomous agent org: `scripts/init_org.py` scaffolds named roles (CEO-human,
  CTO, product manager, product engineering agent, engineers, reviewer) with
  an org chart, status tracking, peer review, escalation, and multi-channel
  demand intake; templates in `assets/org/`, detail in `references/org.md`.
- `scripts/sync_issues.py` — GitHub issue intake for the product engineering
  agent: `pull` open issues into `org/intake/github/` (idempotent, state-tracked)
  and `push` feature tickets.
- Expense-tracker static demo app (`examples/expense-tracker/`): a working
  HTML/CSS/vanilla-JS app with localStorage persistence, deployable to Vercel.
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

- The loop ends at the opened MR/PR: Plan (tracker) → Design → Build → Review.
  The agent never merges, deploys, or releases. `init_workflow.py` no longer
  scaffolds the release hook, control bands, eval runner, or band detector;
  the graph ends at the `implementation` node; SKILL.md, README, playbook,
  graph, adoption, gates README, and plugin metadata say so. Test, Deploy, and
  Maintain tooling stays in the bundle as optional extras.
- Commit and MR/PR: the CLAUDE.md template gains an optional
  `## Commit and MR/PR` section pointing at the project's own commit and
  MR/PR skills or rules, which win over the defaults in
  `references/trackers.md` (repo commit style, the repo's MR/PR template,
  closing keyword). Nothing is committed during Build: one go-ahead at the
  end of Review covers commit, push, and opening the MR/PR. A project style
  skill named in `## Conventions` is invoked in Build and Review.
- The intent lives in the tracker, not the repo: a task on the board is an
  accepted intent, and the agent starts at Design from the task link without
  editing the task. `init_workflow.py` no longer scaffolds `intent/intent.md`
  (`--name` now fills the workflow graph title); the graph's intent node is
  gated by `tracker_board`; `spec.md` and the PR template cite the task ref;
  Maintain drafts new tracker tasks (created on user confirmation) instead of
  writing `intent.md`. `assets/intent.md` is now the shape of a new task
  description.
- `assets/plan.md` — "Files that change" is now a bullet list of exact paths or
  globs so `check_plan_sync.py` can treat the plan as a machine-readable
  manifest.
- `assets/workflow-graph.yaml`, `assets/workflow-graph.example.yaml`, and
  `examples/expense-tracker/workflow-graph.yaml` — nodes now carry
  `done_status` for the workflow state runtime.
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
