# <Title> — Plan

- Task: <task ref> <task link>
- Path: Light | Full (full: spec in docs/changes/<task>/spec.md)
- Status: Draft | Approved
- Approved-by: <user | delegated (YYYY-MM-DD)>
- Date: <YYYY-MM-DD>

<The sections down to Build log are the core — every plan has them. The ones after
"Add only when it applies" are left out until they do.>

## Acceptance criteria

<Light path only — the full path keeps them in spec.md. One per bullet, from the task:>

- AC-1: <observable behavior>

## Files that change

<One path or glob per bullet, no prose. check_plan_sync.py fails for a changed file not listed.>

- src/main.py
- tests/test_main.py

## Shape

<The types and signatures the change adds or changes, stubbed before any test, with why each
has its shape; then each criterion as a call sequence through them. The architect's rounds go
below, one finding per `- [ ]`, resolved as `- [fixed] …` or `- [rejected: <why>] …`, ending
with `Verdict: approved (round <n>)`. When nothing changes shape: `none — <why>`.>

- <type or signature> — <why this shape>

Walkthrough:

- AC-1: <call sequence through the signatures>

### Round 1

- [ ] <BLOCKER|CHANGE|NIT> <path:line> — <finding> → <the shape asked for>

## Order of work

<One slice per criterion: failing test → least code → green. For a refactor, characterization tests first.>

1. AC-1: write `<test id>` → expect it to fail with "<expected failure>" → implement → green

## Proof

<Each criterion → the command that proves it. check_tdd.py runs it: green with the change,
red without. Kept behavior is `regression:` (green only); `manual:` for evidence in the MR/PR.>

- AC-1: <criterion> — `<command that runs just this test>`

## Verification

<Commands and healthy output; the suite's result before the change is the baseline.>

- Typecheck: `<command>` — zero errors (tests included)
- Lint: `<command>` — zero warnings
- Tests: `<command>` — baseline <n passed, m failed> → after <…>

## Build log

<Per slice: the test, the failing line, why that failure was the expected one; then the green run.>

## Review

<One "### Round <n>" per review round: findings fixed (file:line → fix), findings rejected with
a reason, and each acceptance criterion with its evidence.>

---

Add only when it applies:

## Impact

<When the change touches widely used code: from `python3 scripts/impact_map.py --from-plan`,
the callers at risk and the test that covers them.>

- <path> — <callers at risk> — covered by <test or AC-n>

## Test changes

<When an existing test is edited or deleted: the path and why the test itself was wrong.
check_diff_hygiene.py fails for a rewritten test not listed here.>

## Surviving mutants

<When check_mutations.py reports a mutant no test can kill: `path:line — reason`.>

## Assumptions (delegated)

<Delegated mode: questions answered without asking, one line each:
`<question> → <answer taken> — <why> [<source>]`. On the full path, the spec holds the Design ones.>

## Deviations

<When the work departs from this plan or a frozen signature: what and why.>

## Learnings

<As they come up: `- [ ] <kind>: <one line>`. Triaged in Review as
`- [promoted → <store>: <path>] …` or `- [dropped: <why>] …`; check_diff_hygiene.py fails
while a `- [ ]` is left.>
