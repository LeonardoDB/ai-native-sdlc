# Playbook — each step in detail

The loop: **task link → Design → Plan → Shape → Build → Review → MR/PR opened**. Read the section for the step you are entering. Resolving the link, the workspace, and delivery are in `references/trackers.md`. In delegated mode, every "the user approves" below becomes `references/autonomy.md`: you approve, record it, and escalate what it lists.

## Size the change

Before Design, pick the path and say which one and why, so the user can pull you back:

- **Light** — a localized bug, a config change, a small edit inside one module: no spec. plan.md holds the acceptance criteria and is the one approval. Bugs follow `references/debugging.md`: reproduce as a failing test, gather evidence, one hypothesis at a time, the root cause in the plan before the fix.
- **Full** — a feature, a behavior change users will notice, or anything crossing modules or touching data: spec, then plan, each approved.

When in doubt, take the full path; a spec that turns out short costs little.

## Design (full path)

1. Read the task — description, labels, comments, acceptance criteria — with the organization's skills available.
2. **Explore** when the area is unfamiliar: dispatch the explorer (`references/agents/explorer.md`) — one lens for a contained area; two or three distinct lenses (a similar existing feature, the current implementation, the data flow) for a cross-cutting change. Then **read the essential files it flags yourself**: the explorer locates, you understand. Skip it for code you already know.
3. **Recall** from the knowledge stores CLAUDE.md declares (`references/knowledge.md`; the repo's docs when it declares none) — prior decisions, domain rules, glossary terms. Cite each hit. Settled decisions are extended, not re-decided; a conflict with the task is an open question.
4. Write `docs/changes/<task>/spec.md` from `assets/spec.md`: requirements, design, gotchas, areas of concern. The header cites the task (`Intent: <ref> <link>`) and the knowledge used.
5. Gaps in the task become open questions in the spec or questions to the user — never edits to the task. In delegated mode, answer them yourself under `## Assumptions (delegated)`, with a source for each, unless they must escalate.
6. **Gate.** The user reviews the spec against the task and approves it; then set `Status: Approved`.

## Plan

In plan mode, with the task and spec.md (on the light path, the task alone), write `docs/changes/<task>/plan.md` from `assets/plan.md`. The core is short:

- **Files that change** — one path or glob per bullet; `check_plan_sync.py` fails for a changed file not listed.
- **Order of work** — vertical slices, one acceptance criterion each.
- **Proof** — each criterion → the command that proves it (or `manual:` evidence).
- **Verification** — the build, typecheck, lint, and test commands.

Add the other sections only when they apply (the template says when). Interrogate the plan before asking for approval: what could this break, which step is riskiest, what options were rejected? It is done when an engineer who never saw the conversation could build from it. For a change touching widely used code, `python3 scripts/impact_map.py --from-plan` lists who imports and calls the files it will change — leads to read, not a verdict; put the callers at risk under `## Impact` with the test that covers them.

**Gate.** The user approves the plan; then set `Status: Approved`. When the work later departs from it, update plan.md in the same change.

## Shape — types and signatures before code

After the plan is approved, and before any test: when the change adds or changes types, schemas, interfaces, or function signatures, write only those, in the real files, with stub bodies (`raise NotImplementedError`, `throw new Error("unimplemented")`, `todo!()`) and doc comments that say what each promises — inputs, output, the errors it can return. The typecheck passes on the skeleton. Under plan.md's `## Shape`, list the declarations with why each has its shape, and walk every acceptance criterion as a call sequence through them.

Then dispatch the **architect** (`references/agents/architect.md`) in a fresh context. It judges the domain model, names, signatures, errors, boundaries, fit with the codebase, and whether every criterion can be expressed, and returns findings (BLOCKER, CHANGE, NIT) with the shape it would write, plus a verdict. Nits are welcome here: a name changed now costs nothing.

1. Record the round in `## Shape` as `### Round <n>`, one `- [ ]` per finding.
2. Resolve each: change the skeleton and mark it `- [fixed]`, or `- [rejected: <why>]`. Re-run the typecheck.
3. Dispatch a fresh architect with the previous rounds until it returns `APPROVED` (no BLOCKER or CHANGE left); record `Verdict: approved (round <n>)`.
4. At most two rounds. Still not approved, bring the open findings to the user: a shape that will not converge points at the plan or the task.

Show the user the approved shape before the first slice. From then on the signatures are frozen: changing one is a Deviation in plan.md. A change with no new or changed signatures — a config value, a fix inside one function body — writes `none — <why>` and goes straight to Build. `check_diff_hygiene.py` fails on an open finding or a missing verdict; `tracker_link.py` resumes at `shape` until it is there.

The idea is type-driven development (Brady's *type, define, refine*) with a design inspection before the code inspection.

## Build — one slice at a time

**Before the first slice**, record the baseline: run the suite, typecheck, and lint, and note the result under Verification. A failure that exists before the change is named there, not blamed on it later. If CLAUDE.md names a style skill in `## Conventions`, invoke it and repeat it in every subagent brief; if it names an LSP or docs tool in `## Code tooling`, use them.

Each acceptance criterion is a slice: **one failing test → the least code that passes it → green**, then the next. Never all tests first and all code after — tests written in bulk describe imagined behavior.

Dispatch each slice to the **builder** (`references/agents/builder.md`) on the model `## Models` names (default `sonnet`): the design is settled, and the checks and the reviewer catch what it gets wrong. One slice per dispatch. When it returns, re-run the slice's test, read the diff, and write its red evidence into the Build log. When it stops on a frozen signature, an unplanned file, or a broken test, you decide: a Deviation, back to the architect, or the slice yourself. With `builder: inherit`, build the slices in the session.

- **Red first, for the right reason.** The new test fails because the behavior is missing — not a typo, an import path, or a broken fixture.
- **Name the production change that would make the test fail.** If none would, the test tests nothing. Expected values are independent literals, never recomputed the way the code computes them.
- **Test at the public interface.** Mock only at system boundaries — external APIs, time, randomness — never the project's own modules.
- **Fix the code, not the test.** A test is edited only when the test itself is wrong, and the edit goes under Test changes with the reason.
- **Refactors start with characterization** — pin today's behavior with tests first. Clean up after green, not in the middle of a slice.
- **The type checker is a gate.** No `any`, casts, or suppressions to make it pass; when one is truly needed, the same line says why (`reason: …`).
- Append anything worth keeping — a gotcha, a decision, a convention — to `## Learnings` as one `- [ ]` line the moment it appears.

Nothing is committed during Build; the change stays in the working tree until Review is done.

## Review — to the opened MR/PR

1. **Run the checks** and fix what they catch before any reviewer spends time on it:

   ```bash
   python3 scripts/check_plan_sync.py --hook   # the approved plan covers every changed file
   python3 scripts/check_tdd.py                 # every criterion has proof; green with the change, red without
   python3 scripts/check_diff_hygiene.py        # no unexplained suppressions, skips, rewritten tests; shape and learnings resolved
   ```

   plus the typecheck and the full suite against the baseline. `check_tdd.py` runs each Proof command on the change (green), then removes the implementation files — keeping the tests — and runs them again (red); a test that passes without the change fails the check. A criterion that keeps behavior the code already has ("orders under 100 still pay 5") cannot go red: mark it `regression:` and it is checked green only. Optionally, `check_mutations.py` makes small mistakes on the changed lines (`>=` → `>`, `and` → `or`, `100` → `101`) and fails when the tests still pass; list equivalent survivors under `## Surviving mutants` with the reason.
2. **Dispatch the reviewer** (`references/agents/reviewer.md`) in a fresh context with the diff, spec and plan, the acceptance criteria, the check outputs, `REVIEW.md`, the CLAUDE.md rules, and a do-not-flag list (departures already in plan.md). One reviewer with all lenses for a small diff; three in parallel — correctness, spec + conventions, simplicity + security — when each has real surface. For a trivial diff, review it yourself and say so.
3. **Filter.** Dedupe; keep confidence ≥ 80; read the code for lower-confidence high-severity findings and keep or drop them on evidence; drop the rest. Record every rejection with a reason in plan.md's `## Review`, so a second round does not re-raise it.
4. **Walk the task's acceptance criteria** — the task's, not just the plan's — and point at the evidence for each: its `check_tdd.py` line, or the manual walkthrough.
5. **Fix and re-verify.** A behavior found missing gets its own red → green slice. Re-run the checks and keep the output as evidence. Auth, secrets, or payments get a dedicated security review on top.
6. **Triage the learnings.** Each `- [ ]` under `## Learnings` is promoted to the store that fits or dropped with a reason (`references/knowledge.md`).
7. **At most two rounds.** Blockers still standing after the second go to the user.
8. **Ask once:** *commit, push, and open the MR/PR?* One go-ahead covers it all. In delegated mode, don't ask: the MR/PR opens as a draft with a `## Delegated decisions` section.
9. **Deliver** with the project's own skills when CLAUDE.md names them in `## Commit and MR/PR`, otherwise the defaults in `references/trackers.md`. Then **stop**. When the team's review comes back, the MR/PR link starts one feedback round (`references/feedback.md`).

When a review flags a mistake for the second time, the correction goes into CLAUDE.md as part of that review.

## MR/PR CI

The same checks run on a clean checkout against the base:

```bash
python3 scripts/check_plan_sync.py --base origin/main --head HEAD
python3 scripts/check_tdd.py --base origin/main
python3 scripts/check_diff_hygiene.py --base origin/main
```

`check_plan_sync.py` reads the `docs/changes/*/plan.md` the diff touches; in hook mode, when the plan went in an earlier commit, the folder named by the branch (`feat/eng-123-csv-export` → `docs/changes/eng-123/`); `--plan <path>` overrides both. Process files (`docs/`, `REVIEW.md`, `CLAUDE.md`, `AGENTS.md`, `.github/`, `.gitlab/`, READMEs) never need a plan.
