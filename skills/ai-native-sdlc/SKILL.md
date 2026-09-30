---
name: ai-native-sdlc
version: 0.2.0
description: Take a tracker task to a reviewed, opened MR/PR — Design, Plan, Shape, Build, Review — with versioned artifacts and human approval gates at every handoff; the loop ends when the MR/PR is opened, never at merge or deploy. Use when the user passes a Linear, GitLab, or GitHub task link, or states a goal, idea, feature, or change request, and expects the agent to drive the work to an MR/PR instead of jumping straight to code.
---

# AI-Native SDLC

Take a task from the tracker to an opened, verified MR/PR:

```
task link → Design → Plan → Shape → Build → Review → MR/PR opened ■ end
```

You do the generating, verifying, and mechanical work; the user approves at each gate. The loop ends when the MR/PR is opened — merge, deploy, and release belong to the team. `hooks/gate.py` enforces that: merges, pushes to the default branch, `--no-verify`, and bare force-pushes are blocked, and a task branch is published only with the checks passing.

## The loop

Each step says what to do; `references/playbook.md` has the detail for each one.

1. **Resolve** — `scripts/tracker_link.py parse <link>` gives the task ref, `slug`, `change_dir` (`docs/changes/<slug>`), the git state, and `state.next` to resume from (`design`, `approve-spec`, `plan`, `approve-plan`, `shape`, `implement`). A board or epic link exits 1: ask for the task link. Read the task through the tracker's CLI or MCP connector (`references/trackers.md`); never edit it.
2. **Workspace** — before reading code. On the task's branch: continue. Otherwise, with a clean tree, propose `<type>/<slug>-<summary>` off the default branch and create it when the user confirms. A dirty tree stops here.
3. **Size** — say which path and why. **Light** (a localized bug, config, a small edit in one module): no spec, plan.md only. **Full** (a feature, a behavior change, anything crossing modules): spec, then plan. When in doubt, full. A bug starts from `references/debugging.md`.
4. **Design** (full path) — explorer first if the code is unfamiliar; recall from the knowledge stores (`references/knowledge.md`); write `<change_dir>/spec.md` from `assets/spec.md`. **Gate: spec approved.**
5. **Plan** — in plan mode, write `<change_dir>/plan.md` from `assets/plan.md`: files that change, order of work, proof per acceptance criterion. **Gate: plan approved.**
6. **Shape** — when the change adds or changes types or signatures: write them as stubs, walk each acceptance criterion through them, and loop with the architect until it approves (at most two rounds, then the user decides). Otherwise write `none — <why>`. **Gate: architect's verdict.**
7. **Build** — record the baseline (suite, typecheck, lint), then one acceptance criterion at a time, red → green, each slice dispatched to the builder and verified by you. Nothing is committed yet.
8. **Review** — the checks (`check_plan_sync.py --hook`, `check_tdd.py`, `check_diff_hygiene.py`, typecheck, suite against the baseline), then the reviewer in a fresh context; filter its findings, walk the acceptance criteria with evidence, fix, re-verify — at most two rounds. Triage plan.md's `## Learnings`.
9. **Deliver** — ask once: *commit, push, and open the MR/PR?* Use the project's commit and MR/PR skills if CLAUDE.md names them, else the defaults in `references/trackers.md`, with the closing keyword (`Closes group/project#42`, `Fixes ENG-123`). Then stop.

Other starting points: an **MR/PR link** runs one feedback round (`references/feedback.md`); an **idea with no task** starts with an interview, a task drafted in the shape of `assets/intent.md`, and created in the tracker only after the user confirms. If the user is already in a later phase ("review this MR"), start there.

## Hard rules

1. **Gates are real.** Do not pass a gate without the user's approval (or the architect's verdict, for Shape). Record it as `Status: Approved` only when the user said so.
2. **Stop at the MR/PR.** Never merge, deploy, release, or change production config.
3. **Plan first.** Nothing is implemented without an approved plan. When the work departs from it, update plan.md in the same change.
4. **Shape before code.** New or changed types and signatures are stubbed and approved by the architect before any test or implementation; after that they are frozen, and changing one is a Deviation.
5. **Test first, typed.** Every acceptance criterion has a test that fails without the change and passes with it, written before the code. Fix the code, not the test. No `any`, casts, or suppressions without a `reason:` on the same line.
6. **Verify before asking.** Run the checks, build, tests, and lint yourself; fix what fails; only then ask to open the MR/PR.
7. **Evidence, not assertions.** Every finding cites `file:line` and what shows it; every acceptance criterion points at its proof.
8. **Subagents are named and bounded.** Say why you dispatch one and which model it runs on, give it a bounded deliverable, and summarize what it returned.
9. **Encode repeated lessons.** The same mistake twice → the correction goes into CLAUDE.md, a skill, or a hook.

## Subagents

Dispatch each with the Agent tool: its brief from `references/agents/`, plus the context the brief lists (subagents read no config). Run the session itself on the strongest model — it writes the spec and plan, resolves the shape, and filters the review. Each role's model comes from CLAUDE.md's `## Models` (`<role>: <model>`, `inherit` for the session's), else:

| Role | When | Model | Returns |
|---|---|---|---|
| explorer | Design, unfamiliar code | `sonnet` | a `file:line` map and the essential files — read them yourself |
| architect | Shape, a fresh one each round | `inherit` | findings (BLOCKER, CHANGE, NIT) and a verdict — resolve each as fixed or rejected with a reason |
| builder | Build, one slice per dispatch | `sonnet` | red and green evidence — re-run the test and read the diff; `builder: inherit` builds in the session |
| reviewer | Review, fresh context | `inherit` | scored findings — keep confidence ≥ 80, check high-severity lower ones yourself, drop the rest with a reason |

Only the builder writes code. Without the Agent tool, run the brief yourself on only the artifacts it lists, and say so.

## Artifacts

- **The task** — in the tracker; the accepted intent. Never edited.
- **`docs/changes/<task>/spec.md`** (full path) and **`plan.md`** — one folder per task, so parallel branches never touch the same files.
- **The commits and the MR/PR** — citing the task ref.

## Scripts

- `scripts/tracker_link.py` — resolve a task link; where the task stands
- `scripts/check_plan_sync.py` — the approved plan covers every changed file
- `scripts/check_tdd.py` — every criterion has proof; each test is green with the change and red without it
- `scripts/check_diff_hygiene.py` — no unexplained suppressions, skips, or rewritten tests; no open architect finding; learnings triaged
- `scripts/check_mutations.py` — optional: small mistakes on the changed lines must fail a test
- `scripts/impact_map.py` — optional, in Plan: who depends on the files the change touches
- `scripts/init_workflow.py` — scaffold CLAUDE.md, REVIEW.md, and the checks into a repo
- `hooks/gate.py` — the PreToolUse hook behind rule 2 and the publish gate

## References

| Read | When |
|---|---|
| `references/playbook.md` | each step in detail |
| `references/trackers.md` | reading a task, the workspace, delivery defaults |
| `references/knowledge.md` | the repo declares knowledge stores |
| `references/debugging.md` | the task is a bug |
| `references/feedback.md` | the user passes an MR/PR link |
| `references/adoption.md` | tailoring the workflow to a team; how each rule is enforced |
