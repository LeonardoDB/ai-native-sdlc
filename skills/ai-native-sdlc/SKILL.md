---
name: ai-native-sdlc
version: 0.1.0
description: Take a tracker task to a reviewed, opened MR/PR — Plan (the tracker board), Design, Build, Review — with versioned artifacts and human approval gates at every handoff; the loop ends when the MR/PR is opened, never at merge or deploy. Use when the user passes a Linear, GitLab, or GitHub task link, or states a goal, idea, feature, or change request, and expects the agent to drive the work to an MR/PR instead of jumping straight to code.
---

# AI-Native SDLC

Take a task from the tracker board to an opened, verified MR/PR by running the first half of Anthropic's AI-Native SDLC playbook: **Plan (tracker) → Design → Build → Review → MR/PR opened**.

Every phase ends by committing a versioned artifact to git; the next phase starts by reading it. The commit chain is the audit trail: who asked, what the agent produced, and who approved. The agent does the generating, verifying, and mechanical work. Humans keep the judgment calls and the final approvals.

## Where the loop ends

**The loop ends when the MR/PR is opened.** Opening it is the agent's last action. Merge, deploy, release, and production monitoring are outside this workflow: they belong to the team and its own pipeline, and the agent never merges, deploys, or releases.

The upstream playbook continues into Test (evals), Deploy, and Maintain. This bundle still ships those tools — the release gate hook, control bands, the eval runner, incident and runbook templates — as **optional extras**: they are not scaffolded, not part of the default flow, and only used when the user explicitly asks for them. Their reference material stays in `references/playbook.md` (Phases 4–6).

## Frameworks

The workflow is framework-agnostic. Claude Code calls the repository-memory file `CLAUDE.md` and keeps skills in `.claude/skills/`; Codex calls the repository-memory file `AGENTS.md` and installs skills into `~/.codex/skills/`. Wherever this skill says CLAUDE.md, use the repository-memory file your framework recognizes. The same skill folder installs in either environment, and the artifacts (`spec.md`, `plan.md`, `REVIEW.md`) are framework-neutral. The intent is not a repo artifact: it lives in the tracker.

## Hard rules

1. **Human gates are real gates.** Do not advance without approval: task on the board (accepted intent) → Design; spec approved → Build; plan approved → code.
2. **Stop at the MR/PR.** Open it and stop. Never merge, deploy, release, or change production config; those are the team's decisions, outside this workflow.
3. **Verify before asking for review.** Run build, tests, lint, and screenshots yourself first; fix what fails; only then ask to commit and open the MR/PR.
4. **Encode repeated lessons.** The same mistake twice → write the correction into the project's CLAUDE.md, a skill, or a hook.
5. **Evidence in reviews.** Every finding cites file/line and concrete evidence, ordered by severity, with at most 5 nit comments per review.
6. **Plan mode first.** Nothing is implemented without an accepted plan; when implementation departs from the plan, update plan.md in the same commit.
7. **Reviews feed back.** When a review flags a mistake for the second time, the correction goes into CLAUDE.md as part of that review.
8. **Subagents are named, visible, and accountable.** Scaffold subagents only with a functional name, a committed definition, an explained dispatch, and a bounded report with evidence — never a silent background worker that can idle or act on stale context.

## Rule → enforcement matrix

Each hard rule is backed by an advisory layer (makes compliance likely), a
deterministic layer (makes violation nearly impossible), or a review pass
(checked at a gate). Use this when compliance asks "how is this enforced?"

| Hard rule | Advisory (skill/CLAUDE.md) | Deterministic (hook/file) | Checked at |
|---|---|---|---|
| 1. Gates are real | CLAUDE.md conventions | committed artifact chain in git; gate ledger (`gate_ledger.py`) | gate acceptance commits |
| 2. Stop at the MR/PR | this skill | branch protection on the forge (the agent cannot merge its own MR/PR); optional `production-gate.sh` hook | MR/PR opened |
| 3. Verify before review | CLAUDE.md "Verifying your work" | single `make`-style verify commands | MR/PR template evidence |
| 4. Encode repeated lessons | CLAUDE.md "Things the agent gets wrong" | protected-path hooks | second-time-mistake rule in reviews |
| 5. Evidence in reviews | REVIEW.md | — | review passes, 5-nit cap |
| 6. Plan mode first | plan.md template | `check_plan_sync.py` (optional pre-commit hook / MR/PR gate) | plan-vs-diff check in review |
| 7. Reviews feed back | CLAUDE.md | — | review comments → CLAUDE.md |
| 8. Subagents named/visible | this hard rule | subagent definitions committed in git | subagent reports in session |

Anything in the deterministic column must always hold — enforce it with code,
not prose.

## Starting from a task link

The intent lives in the tracker (Linear, GitLab, GitHub), not in the repo. A task on the board is an accepted intent — refined and prioritized there — so the board is the Plan gate and the agent starts at Design.

1. From the repo you are working in, resolve the link with `scripts/tracker_link.py parse <link>`: system, native ref (`ENG-123`, `group/project#42`), and whether the task belongs to this repo. Detection is by link shape (GitLab's `/-/`, `linear.app`, `github.com`), so self-hosted GitLab needs no config. A board, epic, or unrecognized link exits 1 — ask for the task link instead.
2. Read the task (description, labels, comments) through the tracker's MCP connector or CLI. Never edit it: gaps become open questions in `spec.md` or questions to the user.
3. Run **Design** in that repo. If its CLAUDE.md has a `## Knowledge base` section, search it first for what the task touches — prior decisions, domain terms, known constraints. `spec.md` cites the task (`Intent: <ref> <link>`) and the knowledge used; a conflict between the task and the knowledge base becomes an open question.
4. Run **Build** and **Review**, invoking the project's style skill if `## Conventions` names one (and repeating that instruction in every subagent brief). Do not commit along the way.
5. When Review is done, ask once: *commit, push, and open the MR/PR?* On the go-ahead, commit and open it with the project's own skills when its CLAUDE.md names them in `## Commit and MR/PR`; otherwise follow the defaults in `references/trackers.md` (repo commit style, the repo's MR/PR template, the closing keyword `Closes group/project#42` / `Fixes ENG-123`). Then stop.

Read `references/trackers.md` for per-tracker read commands, the rules, and the optional per-project `## Tracker` section in CLAUDE.md for exceptions (issues in a different project than the code).

## Starting from an idea

When the user brings a goal or idea with no task yet:

1. Scaffold the artifact skeleton if the repo has none: `scripts/init_workflow.py <project-dir> --name "<project name>" --framework codex|claude` (codex writes AGENTS.md, claude writes CLAUDE.md), or copy templates from `assets/` into an existing repo.
2. Run **Plan**: interview the user with analyst-style questions — what cannot be done today, who is affected, what success looks like, constraints, what is out of scope — until the idea is concrete.
3. Draft the task description in the shape of `assets/intent.md` and create it in the tracker only after the user confirms. It enters the loop once it is on the board.

If the user is already inside a later phase (for example, "review this MR"), start at that phase instead.

## Running the loop

Read `references/playbook.md` for the phase-by-phase procedure: Phases 1–3 cover Plan, Design, and Build; the "AI in the PR review loop" section of Phase 5 covers Review.

At a glance:

| Phase | Reads | Produces | Gate |
|---|---|---|---|
| Plan | the tracker board | task on the board (no repo artifact) | on the board → Design |
| Design | tracker task + org standards + knowledge base (if declared) | spec.md | spec approved → Build |
| Build | tracker task + spec.md + style skill (if declared) | plan.md → code + tests (uncommitted) | plan approved before code |
| Review | diff + spec.md + plan.md + REVIEW.md + style skill (if declared) | findings fixed; verify output; commits + MR/PR opened (project's commit/MR skills if declared) | one go-ahead to commit, push, and open; **end of the loop** — the team reviews and merges |

## Graph engineering

The loop is a directed graph, not a linear pipeline: plays and artifacts are nodes, gates are the human approval points, and triggers are the edges that fire the next stage. Treating the workflow as a graph makes it automatable (accepted artifacts fire the next gate), parallelizable (independent branches run in separate worktrees), and auditable (node history is the record). Read `references/graph.md` when designing or automating how phases trigger each other; the machine-readable form ships in `assets/workflow-graph.example.yaml`, ending at the `implementation` node (MR/PR).

## Autonomous agent org

For teams that want the loop to run with less human steering, the skill can
scaffold an **agent org**: named roles (CEO-human, CTO, product manager,
product engineering agent, engineers, reviewer) with an org chart, a reporting
protocol, peer review of every artifact, and multi-channel demand intake
(GitHub issues, forms, email). Agents run the phases, review each other's work,
and escalate to the human CEO at the critical gates (intent ambiguity,
unresolved disagreement, MR/PR merge). Scaffold it with
`scripts/init_org.py <project-dir>`; full detail in `references/org.md`.

## Templates and assets

The scaffold script copies the core skeleton into a project: `CLAUDE.md`/`AGENTS.md`,
`REVIEW.md`, `workflow-graph.yaml`, `.gitignore`, `gates/README.md`, and the tool
scripts `gate_ledger.py`/`workflow_state.py`/`check_plan_sync.py`. No `intent.md` —
the intent lives in the tracker — and nothing for deploy or monitoring. `spec.md` and
`plan.md` are produced by the workflow itself during Design and Build — copy the
blank forms only when you want them as starting points:

- `assets/intent.md` — shape of a new tracker task description (problem, proposed outcome, affected users/systems, constraints, out of scope, open questions); not copied into projects
- `assets/spec.md` — requirements + design specification with gotchas (produced during Design)
- `assets/plan.md` — build plan (files, order, risks, proof, verification) (produced during Build)
- `assets/CLAUDE.md` — repository-memory starter (commands, verification, conventions, common mistakes, optional Tracker, Knowledge base, and Commit and MR/PR sections)
- `assets/REVIEW.md` — review standards (passes, evidence, severity, 5-nit cap)
- `assets/PULL_REQUEST_TEMPLATE.md` — MR/PR description mapped to REVIEW.md passes + evidence
- `assets/gates-README.md` — gate ledger usage (copied into new projects as `gates/README.md`)
- `assets/workflow-graph.example.yaml` — the loop as a directed graph (nodes, gates, trigger edges)
- `assets/workflow-graph.yaml` — blank project graph state (copied into new projects)
- `assets/org/` — agent org templates (org chart, status, role cards, protocol, intake, review records; copied by `scripts/init_org.py`)

**Optional extras — outside the loop, not scaffolded.** Use only when the user asks for evals, a release gate, or monitoring:

- `assets/production-gate.sh` + `assets/hook-settings.example.json` — release authorization hook and its wiring (deploy-action patterns, expiry, ledger-backed approvals)
- `assets/managed-settings.example.json` — regulated-enterprise managed settings
- `assets/evals.example.md`, `assets/evals.example.json`, `assets/evals-README.md`, `assets/agent-evals.yml.example` — eval suite format and CI workflow for `scripts/run_evals.py`
- `assets/bands.yaml`, `assets/incident.md`, `assets/runbooks/` — control bands, incident record, and pre-approved runbooks for monitoring

## Scripts

In the loop:

- `scripts/tracker_link.py` — resolve a Linear/GitLab/GitHub task link to system and native ref, and check it against the current repo's `origin` (no config, offline, deterministic; boards and epics exit 1)
- `scripts/init_workflow.py` — scaffold the artifact skeleton into a project (`--dry-run`, `--framework`, `--git`)
- `scripts/gate_ledger.py` — hash-chained approval ledger: every gate decision is a committed, tamper-evident record
- `scripts/workflow_state.py` — deterministic workflow state runtime (`status`/`advance`/`check`): graph nodes advance only through matching, chain-verified ledger records
- `scripts/check_plan_sync.py` — deterministic plan-sync enforcement: implementation changes require an approved plan.md manifest in MR/PR/CI or pre-commit mode
- `scripts/quick_validate.py` — validate the skill/plugin bundle (self-check; CI runs it)

Agent org (optional): `scripts/init_org.py` (scaffold), `scripts/sync_issues.py` (GitHub issue intake), `scripts/org_status.py` (busy/idle and review queue), `scripts/intake.py` (form/email intake).

Optional extras, outside the loop: `scripts/run_evals.py` (eval suite runner with `--min-pass-rate` gating) and `scripts/detect_bands.py` (deterministic control-band detection).

## Self-test (after installing)

1. `python3 skills/ai-native-sdlc/scripts/init_workflow.py /tmp/wf-demo --name "Demo" --git`
2. Tell your agent: *run the AI-native SDLC workflow for <task link>.*
3. Approve the spec and the plan, and confirm the agent stops at every gate and
   stops for good once the MR/PR is opened — no merge, no deploy.

## Customization

Read `references/adoption.md` when tailoring the workflow to an organization or when asked how to roll this out gradually. It covers staged adoption, encoding org standards as skills, wiring hooks, and keeping existing tools (Jira, Figma, GitHub, Slack) in place.
