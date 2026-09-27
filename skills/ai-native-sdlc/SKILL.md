---
name: ai-native-sdlc
version: 0.1.0
description: Take a tracker task to a reviewed, opened MR/PR — Plan (the tracker board), Design, Build, Review — with versioned artifacts and human approval gates at every handoff; the loop ends when the MR/PR is opened, never at merge or deploy. Use when the user passes a Linear, GitLab, or GitHub task link, or states a goal, idea, feature, or change request, and expects the agent to drive the work to an MR/PR instead of jumping straight to code.
---

# AI-Native SDLC

Take a task from the tracker board to an opened, verified MR/PR by running the first half of Anthropic's AI-Native SDLC playbook: **Plan (tracker) → Design → Build → Review → MR/PR opened**.

Every phase ends with a versioned artifact the next phase reads. The agent does the generating, verifying, and mechanical work. Humans keep the judgment calls and the approvals.

## Where the loop ends

**The loop ends when the MR/PR is opened.** Opening it is the agent's last action. Merge, deploy, release, and production monitoring are outside this workflow: they belong to the team and its own pipeline, and the agent never merges, deploys, or releases.

## Artifacts

- **Intent** — the tracker task itself (Linear, GitLab, GitHub). Not a repo file; the agent never edits it.
- **`docs/changes/<task>/spec.md`** and **`docs/changes/<task>/plan.md`** — one folder per task, so parallel branches in one repo never touch the same files. `<task>` is the `slug` from `tracker_link.py` (`eng-123`, `42`, `backlog-42`).
- **Commits and the MR/PR** — citing the task ref, closing the task on merge.

## Frameworks

The workflow is framework-agnostic. Claude Code calls the repository-memory file `CLAUDE.md` and keeps skills in `.claude/skills/`; Codex calls the repository-memory file `AGENTS.md` and installs skills into `~/.codex/skills/`. Wherever this skill says CLAUDE.md, use the repository-memory file your framework recognizes. The same skill folder installs in either environment.

## Hard rules

1. **Human gates are real gates.** Do not advance without approval: task on the board (accepted intent) → Design; spec approved → Build; plan approved → code.
2. **Stop at the MR/PR.** Open it and stop. Never merge, deploy, release, or change production config; those are the team's decisions, outside this workflow.
3. **Verify before asking for review.** Run build, tests, lint, and screenshots yourself first; fix what fails; only then ask to commit and open the MR/PR.
4. **Encode repeated lessons.** The same mistake twice → write the correction into the project's CLAUDE.md, a skill, or a hook.
5. **Evidence in reviews.** Every finding cites file/line and concrete evidence, ordered by severity, with at most 5 nit comments per review.
6. **Plan mode first.** Nothing is implemented without an accepted plan; when implementation departs from the plan, update plan.md in the same change.
7. **Reviews feed back.** When a review flags a mistake for the second time, the correction goes into CLAUDE.md as part of that review.
8. **Subagents are named, visible, and accountable.** Dispatch subagents only with a functional name, an explained dispatch, and a bounded report with evidence — never a silent background worker that can idle or act on stale context.

## Rule → enforcement matrix

Each hard rule is backed by an advisory layer (makes compliance likely), a
deterministic layer (makes violation nearly impossible), or a review pass
(checked at a gate). Use this when someone asks "how is this enforced?"

| Hard rule | Advisory (skill/CLAUDE.md) | Deterministic (hook/file) | Checked at |
|---|---|---|---|
| 1. Gates are real | this skill | the board holds the task; `Status: Approved` in spec.md and plan.md | spec and plan approval |
| 2. Stop at the MR/PR | this skill | branch protection on the forge (the agent cannot merge its own MR/PR) | MR/PR opened |
| 3. Verify before review | CLAUDE.md "Verifying your work" | single `make`-style verify commands | MR/PR template evidence |
| 4. Encode repeated lessons | CLAUDE.md "Things the agent gets wrong" | protected-path hooks | second-time-mistake rule in reviews |
| 5. Evidence in reviews | REVIEW.md | — | review passes, 5-nit cap |
| 6. Plan mode first | plan.md template | `check_plan_sync.py` (pre-commit hook / MR/PR CI) | plan-vs-diff check in review |
| 7. Reviews feed back | CLAUDE.md | — | review comments → CLAUDE.md |
| 8. Subagents named/visible | this hard rule | — | subagent reports in session |

Anything in the deterministic column must always hold — enforce it with code,
not prose.

## Starting from a task link

The intent lives in the tracker (Linear, GitLab, GitHub), not in the repo. A task on the board is an accepted intent — refined and prioritized there — so the board is the Plan gate and the agent starts at Design.

1. From the repo you are working in, resolve the link with `scripts/tracker_link.py parse <link>`: system, native ref (`ENG-123`, `group/project#42`), whether the task belongs to this repo, and its `change_dir` (`docs/changes/<task>`). Detection is by link shape (GitLab's `/-/`, `linear.app`, `github.com`), so self-hosted GitLab needs no config. A board, epic, or unrecognized link exits 1 — ask for the task link instead.
2. Read the task (description, labels, comments) through the tracker's MCP connector or CLI. Never edit it: gaps become open questions in `spec.md` or questions to the user.
3. Run **Design** in that repo. If its CLAUDE.md has a `## Knowledge base` section, search it first for what the task touches — prior decisions, domain terms, known constraints. Write `<change_dir>/spec.md`, citing the task (`Intent: <ref> <link>`) and the knowledge used; a conflict between the task and the knowledge base becomes an open question.
4. Run **Build** (plan mode → `<change_dir>/plan.md` → code + tests) and **Review**, invoking the project's style skill if `## Conventions` names one (and repeating that instruction in every subagent brief). Do not commit along the way.
5. When Review is done, ask once: *commit, push, and open the MR/PR?* On the go-ahead, commit and open it with the project's own skills when its CLAUDE.md names them in `## Commit and MR/PR`; otherwise follow the defaults in `references/trackers.md` (repo commit style, the repo's MR/PR template, the closing keyword `Closes group/project#42` / `Fixes ENG-123`). Then stop.

Read `references/trackers.md` for per-tracker read commands, the rules, the delivery defaults, and the optional per-project `## Tracker` section in CLAUDE.md for exceptions (issues in a different project than the code).

## Starting from an idea

When the user brings a goal or idea with no task yet:

1. Run **Plan**: interview the user with analyst-style questions — what cannot be done today, who is affected, what success looks like, constraints, what is out of scope — until the idea is concrete.
2. Draft the task description in the shape of `assets/intent.md` and create it in the tracker only after the user confirms. It enters the loop once it is on the board.

If the user is already inside a later phase (for example, "review this MR"), start at that phase instead.

## Running the loop

Read `references/playbook.md` for the phase-by-phase procedure.

| Phase | Reads | Produces | Gate |
|---|---|---|---|
| Plan | the tracker board | task on the board (no repo artifact) | on the board → Design |
| Design | tracker task + org standards + knowledge base (if declared) | `docs/changes/<task>/spec.md` | spec approved → Build |
| Build | tracker task + spec.md + style skill (if declared) | `docs/changes/<task>/plan.md` → code + tests (uncommitted) | plan approved before code |
| Review | diff + spec.md + plan.md + REVIEW.md + style skill (if declared) | findings fixed; verify output; commits + MR/PR opened (project's commit/MR skills if declared) | one go-ahead to commit, push, and open; **end of the loop** — the team reviews and merges |

## Templates

- `assets/intent.md` — shape of a new tracker task description (problem, proposed outcome, affected users/systems, constraints, out of scope, open questions); used only when drafting a task
- `assets/spec.md` — requirements + design specification with gotchas (written during Design)
- `assets/plan.md` — build plan with a machine-readable "Files that change" manifest (written during Build)
- `assets/CLAUDE.md` — repository-memory starter (commands, verification, conventions, and the optional Tracker, Knowledge base, and Commit and MR/PR sections)
- `assets/REVIEW.md` — review standards (passes, evidence, severity, 5-nit cap)
- `assets/PULL_REQUEST_TEMPLATE.md` — fallback MR/PR body when the repo has no template

## Scripts

- `scripts/tracker_link.py` — resolve a Linear/GitLab/GitHub task link to system, native ref, task slug, and `change_dir`, and check it against the current repo's `origin` (no config, offline, deterministic; boards and epics exit 1)
- `scripts/check_plan_sync.py` — deterministic plan-sync: implementation changes need an approved `docs/changes/<task>/plan.md` whose manifest covers them (MR/PR CI with `--base/--head`, or pre-commit with `--hook`)
- `scripts/init_workflow.py` — scaffold `CLAUDE.md`/`AGENTS.md`, `REVIEW.md`, `.gitignore`, and `check_plan_sync.py` into a repo (`--dry-run`, `--framework`, `--git`; existing files are skipped)
- `scripts/quick_validate.py` — validate this skill/plugin bundle (self-check; CI runs it)

## Self-test (after installing)

1. In a repo whose tracker you can read, tell your agent: *run the AI-native SDLC workflow for <task link>.*
2. Approve the spec and the plan, and confirm the agent stops at every gate and
   stops for good once the MR/PR is opened — no merge, no deploy.

## Customization

Read `references/adoption.md` when tailoring the workflow to a team: encoding org standards as skills, wiring hooks, review culture, parallel sessions, and keeping existing tools in place.
