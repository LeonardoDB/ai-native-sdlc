---
name: ai-native-sdlc
version: 0.1.0
description: Take a tracker task to a reviewed, opened MR/PR — Plan (the tracker board), Design, Build, Review — with versioned artifacts and human approval gates at every handoff; the loop ends when the MR/PR is opened, never at merge or deploy. Use when the user passes a Linear, GitLab, or GitHub task link, or states a goal, idea, feature, or change request, and expects the agent to drive the work to an MR/PR instead of jumping straight to code.
---

# AI-Native SDLC

Take a task from the tracker board to an opened, verified MR/PR by running the first half of Anthropic's AI-Native SDLC playbook: **Plan (tracker) → Design → Build → Review → MR/PR opened**.

Every phase ends with a versioned artifact the next phase reads. The agent does the generating, verifying, and mechanical work. Humans keep the judgment calls and the approvals.

## Where the loop ends

**The loop ends when the MR/PR is opened.** Opening it is the agent's last action. Merge, deploy, release, and production monitoring are outside this workflow: they belong to the team and its own pipeline, and the agent never merges, deploys, or releases. With the gate hook wired (`hooks/gate.py`), that is enforced: merges, pushes to the default branch, `--no-verify`, and bare force-pushes are blocked, and publishing a task branch requires the checks to pass.

## Artifacts

- **Intent** — the tracker task itself (Linear, GitLab, GitHub). Not a repo file; the agent never edits it.
- **`docs/changes/<task>/spec.md`** (full path only) and **`docs/changes/<task>/plan.md`** — one folder per task, so parallel branches in one repo never touch the same files. `<task>` is the `slug` from `tracker_link.py` (`eng-123`, `42`, `backlog-42`).
- **Commits and the MR/PR** — citing the task ref, closing the task on merge.

## Frameworks

The workflow is framework-agnostic. Claude Code calls the repository-memory file `CLAUDE.md` and keeps skills in `.claude/skills/`; Codex calls the repository-memory file `AGENTS.md` and installs skills into `~/.codex/skills/`. Wherever this skill says CLAUDE.md, use the repository-memory file your framework recognizes. The same skill folder installs in either environment.

## Hard rules

1. **Human gates are real gates.** Do not advance without approval: task on the board (accepted intent) → Design; spec approved → Build (full path); plan approved → code.
2. **Stop at the MR/PR.** Open it and stop. Never merge, deploy, release, or change production config; those are the team's decisions, outside this workflow.
3. **Verify before asking for review.** Run build, tests, lint, and screenshots yourself first; fix what fails; only then ask to commit and open the MR/PR.
4. **Encode repeated lessons.** The same mistake twice → write the correction into the project's CLAUDE.md, a skill, or a hook.
5. **Evidence in reviews.** Every finding cites file/line and concrete evidence, ordered by severity, with at most 5 nit comments per review.
6. **Plan mode first.** Nothing is implemented without an accepted plan; when implementation departs from the plan, update plan.md in the same change.
7. **Reviews feed back.** When a review flags a mistake for the second time, the correction goes into CLAUDE.md as part of that review.
8. **Subagents are named, visible, and accountable.** Dispatch subagents only with a functional name, an explained dispatch, and a bounded report with evidence — never a silent background worker that can idle or act on stale context.
9. **Test first, typed.** Every acceptance criterion has a test that fails without the change and passes with it, written before the code. Fix the code, not the test. The type checker is a gate: no `any`, casts, or suppressions without a `reason:` on the same line.

## Rule → enforcement matrix

Each hard rule is backed by an advisory layer (makes compliance likely), a
deterministic layer (makes violation nearly impossible), or a review pass
(checked at a gate). Use this when someone asks "how is this enforced?"

| Hard rule | Advisory (skill/CLAUDE.md) | Deterministic (hook/file) | Checked at |
|---|---|---|---|
| 1. Gates are real | this skill | the board holds the task; `Status: Approved` in spec.md and plan.md | spec and plan approval |
| 2. Stop at the MR/PR | this skill | `hooks/gate.py` blocks `glab mr merge`/`gh pr merge`, pushes to the default branch, `--no-verify`, and force-pushes without a lease; branch protection on the forge | MR/PR opened |
| 3. Verify before review | CLAUDE.md "Verifying your work" | single `make`-style verify commands | MR/PR template evidence |
| 4. Encode repeated lessons | CLAUDE.md "Things the agent gets wrong" | protected-path hooks | second-time-mistake rule in reviews |
| 5. Evidence in reviews | REVIEW.md | — | review passes, 5-nit cap |
| 6. Plan mode first | plan.md template | `check_plan_sync.py` (pre-commit hook / MR/PR CI); `impact_map.py --check` (risky paths named in the plan) | plan-vs-diff check in review |
| 7. Reviews feed back | CLAUDE.md | — | review comments → CLAUDE.md |
| 8. Subagents named/visible | this hard rule; briefs in `references/agents/` | — | subagent reports in session |
| 9. Test first, typed | plan.md Proof, Types first, Build log | `check_tdd.py` (AC coverage; green with the change, red without); `check_mutations.py` (mutants on the changed lines must die); `check_diff_hygiene.py` (suppressions, skips, rewritten tests); the project's typecheck | Review, before the reviewer; `hooks/gate.py` before any push or MR/PR; MR/PR CI with `--base` |

Anything in the deterministic column must always hold — enforce it with code,
not prose.

## Starting from a task link

The intent lives in the tracker (Linear, GitLab, GitHub), not in the repo. A task on the board is an accepted intent — refined and prioritized there — so the board is the Plan gate and the agent starts at Design.

1. **Resolve** the link from the repo you are in: `scripts/tracker_link.py parse <link>` gives the system, native ref (`ENG-123`, `group/project#42`), `slug`, `change_dir` (`docs/changes/<slug>`), whether the task belongs to this repo, the git state (branch, default branch, dirty tree), and the task's `state`. Detection is by link shape (GitLab's `/-/`, `linear.app`, `github.com`), so self-hosted GitLab needs no config. A board, epic, or unrecognized link exits 1 — ask for the task link instead.
2. **Read** the task (description, labels, comments, acceptance criteria) through the tracker's MCP connector or CLI. Never edit it: gaps become open questions in the spec or questions to the user.
3. **Workspace** — before reading any code. Already `on_task_branch`: continue. Otherwise, with a clean tree, propose `<type>/<slug>-<summary>` off the fetched `default_branch` and create it once the user confirms; a dirty tree stops here for the user to decide. Offer a worktree only when the user wants the current checkout left alone.
4. **Resume** from `state.next` instead of restarting: `design`, `approve-spec`, `plan`, `approve-plan`, or `implement` (then Review).
5. **Size the change** and say which path you take, so the user can pull you back:
   - **Light** — a localized bug, a config change, a small scoped edit: skip the spec; `plan.md` alone (files, proof, verification), one approval.
   - **Full** — a feature, a behavior change, or anything crossing modules: spec, then plan, each approved.
6. **Design** (full path). If the area is unfamiliar, dispatch the **explorer** first (`references/agents/explorer.md`) — one lens for a contained area, two or three distinct lenses for a cross-cutting one — then read the essential files it flags yourself. If CLAUDE.md has a `## Knowledge base`, search it for what the task touches. Write `<change_dir>/spec.md`, citing the task (`Intent: <ref> <link>`) and the knowledge used; a conflict between the task and the knowledge base becomes an open question.
7. **Build**: plan mode → `<change_dir>/plan.md`, with `## Impact` filled from `impact_map.py --from-plan` (every high-risk file and how its regression is covered) → approval → record the baseline (suite, typecheck, lint) → types first when the change adds domain shapes → one acceptance criterion at a time, red → green, with the red evidence in plan.md's Build log. Invoke the project's style skill if `## Conventions` names one (and repeat it in every subagent brief), and the LSP and docs tools from `## Code tooling`. Nothing is committed yet.
8. **Review**: first the deterministic checks — `check_plan_sync.py --hook`, `check_tdd.py`, `check_mutations.py`, `check_diff_hygiene.py`, `impact_map.py --check`, typecheck, and the suite against the baseline — then the **reviewer** (`references/agents/reviewer.md`) in a fresh context — one reviewer with all lenses for a small diff, three in parallel (correctness, spec + conventions, simplicity + security) when each has real surface; for a trivial diff, review it yourself and say so. Then filter as the coordinator, walk the task's acceptance criteria with evidence, fix, and re-verify — at most two review rounds before surfacing what is still open to the user. Record fixed and rejected findings in plan.md's `## Review`.
9. **Deliver**: ask once — *commit, push, and open the MR/PR?* On the go-ahead, use the project's own skills when CLAUDE.md names them in `## Commit and MR/PR`, otherwise the defaults in `references/trackers.md`; put the closing keyword in the MR/PR (`Closes group/project#42`, `Fixes ENG-123`). Then stop.

Read `references/trackers.md` for per-tracker read commands, the workspace and delivery details, the rules, and the optional `## Tracker` section in CLAUDE.md for exceptions; `references/playbook.md` for each phase in depth.

## Subagents

Two roles, both read-only, dispatched with their brief from `references/agents/` plus the context that brief lists (subagents read no config on their own):

- **explorer** — in Design, for unfamiliar code: returns a `file:line` map and a ranked list of essential files. You still read those files before designing.
- **reviewer** — in Review, always in a fresh context: returns every finding scored by confidence and severity. You are the filter: keep findings at confidence ≥ 80, check lower-confidence high-severity ones in the code yourself, and drop the rest with a one-line reason.

Dispatch them with your framework's subagent mechanism (Claude Code's Agent tool, Codex subagents). Where none is available, run the brief yourself on only the artifacts it lists, and say so. Do not stack further self-check passes on top of one independent review and one verify.

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
| Design (full path) | tracker task + explorer map + knowledge base (if declared) + org standards | `docs/changes/<task>/spec.md` | spec approved → Build |
| Build | tracker task + spec.md (if any) + style skill (if declared) | `docs/changes/<task>/plan.md` → code + tests (uncommitted) | plan approved before code |
| Review | reviewer findings + acceptance criteria + verify output | fixes; plan.md `## Review`; commits + MR/PR opened | one go-ahead to commit, push, and open; **end of the loop** — the team reviews and merges |

## Templates

- `assets/intent.md` — shape of a new tracker task description (problem, proposed outcome, affected users/systems, constraints, out of scope, open questions); used only when drafting a task
- `assets/spec.md` — requirements + design specification with gotchas (written during Design)
- `assets/plan.md` — build plan: "Files that change" manifest, types first, vertical slices, Proof (AC → command), Test changes, baseline, Build log, Review (written during Build)
- `assets/CLAUDE.md` — repository-memory starter (commands including typecheck, verification, conventions, and the optional Code tooling, Tracker, Knowledge base, and Commit and MR/PR sections)
- `assets/REVIEW.md` — review standards (passes, evidence, severity, 5-nit cap)
- `assets/PULL_REQUEST_TEMPLATE.md` — fallback MR/PR body when the repo has no template
- `references/agents/explorer.md`, `references/agents/reviewer.md` — subagent briefs for Design and Review

## Scripts

- `scripts/tracker_link.py` — resolve a Linear/GitLab/GitHub task link to system, native ref, slug, and `change_dir`; check it against the current repo (origin, branch, default branch, dirty tree); report the task's state for resuming (no config, offline, deterministic; boards and epics exit 1)
- `scripts/check_plan_sync.py` — deterministic plan-sync: implementation changes need an approved `docs/changes/<task>/plan.md` whose manifest covers them (MR/PR CI with `--base/--head`, or pre-commit with `--hook`)
- `scripts/check_tdd.py` — deterministic TDD proof: every acceptance criterion maps to a Proof command (or manual evidence); each command passes with the change and fails with the implementation removed (working tree, or `--base` in CI)
- `scripts/check_mutations.py` — mutation check on the changed lines only: flipped comparisons, swapped and/or, off-by-one constants, inverted booleans; a mutant the Proof commands still pass fails unless plan.md lists it under Surviving mutants with a reason
- `scripts/impact_map.py` — dependents (imports), callers of the changed symbols, git-history fix rate, and a high/mid/low risk per file; `--from-plan` before the change, `--check` in Review (every high-risk file named under plan.md's Impact)
- `scripts/check_diff_hygiene.py` — added type/lint suppressions and skipped or focused tests need a `reason:`; rewritten or deleted existing tests must be listed under plan.md's Test changes
- `hooks/gate.py` — Claude Code PreToolUse hook: blocks merges, pushes to the default branch, `--no-verify`, and bare force-pushes; lets a task branch be pushed or its MR/PR opened only on a clean tree with the checks passing (`SDLC_GATE_MUTATIONS=1` adds the mutation check). No Stop hook — red is a normal state mid-slice
- `scripts/init_workflow.py` — scaffold `CLAUDE.md`/`AGENTS.md`, `REVIEW.md`, `.gitignore`, and the check scripts into a repo (`--dry-run`, `--framework`, `--git`; existing files are skipped)
- `scripts/quick_validate.py` — validate this skill/plugin bundle (self-check; CI runs it)

## Self-test (after installing)

1. In a repo whose tracker you can read, tell your agent: *run the AI-native SDLC workflow for <task link>.*
2. Approve the spec and the plan, and confirm the agent stops at every gate and
   stops for good once the MR/PR is opened — no merge, no deploy.

## Customization

Read `references/adoption.md` when tailoring the workflow to a team: encoding org standards as skills, wiring hooks, review culture, parallel sessions, and keeping existing tools in place.
