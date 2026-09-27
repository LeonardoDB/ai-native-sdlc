# <Title> — Build Plan

- Task: <task ref> <task link>
- Path: Light | Full (full: spec in docs/changes/<task>/spec.md)
- Status: Draft | Approved
- Date: <YYYY-MM-DD>

## Acceptance criteria

<Light path only — the full path keeps them in spec.md. One per bullet, numbered, from the task:>

- AC-1: <observable behavior>

## Files that change

<One path or glob per bullet — no prose. Examples:>

- src/main.py
- tests/test_main.py

## Types first

<Only when the change adds new domain shapes (types, schemas, interfaces, public signatures).
List them; they are written first with stub bodies, pass the type-check, are reviewed, and
are then frozen — a later change to one goes under Deviations. Otherwise: "none".>

- <type or signature> — <why this shape: closed values as unions/enums, no invalid states>

## Order of work

<Vertical slices, one acceptance criterion at a time: failing test → minimal code → green.
Never all tests first and all code after. For a refactor, characterization tests come first.>

1. AC-1: write `<test id>` → run it, expect it to fail with "<expected failure>" → implement → green

## Proof

<Every acceptance criterion maps to the command that proves it, or to manual evidence.
check_tdd.py runs each command: it must pass with the change and fail without it.>

- AC-1: <criterion> — `<command that runs just this test>`

## Test changes

<Existing tests edited or deleted, each with the reason (the test contradicted the spec,
the behavior was intentionally removed). Empty when only new tests were added. Fix the
code, not the test: a test is changed only when the test itself is wrong.>

## Deviations

<Departures from this plan or from frozen signatures, each with its reason. Empty by default.>

## Risks

<What could go wrong and how we de-risk it; e.g., "the claims-core API rate-limits at 50 rps; the panel must cache.">

## Verification

<Commands and healthy output. Record the full suite's result before the change as the
baseline; after it, zero new failures, and any pre-existing failure named.>

- Build: `<command>` — <healthy output>
- Typecheck: `<command>` — zero errors (tests included)
- Lint: `<command>` — zero warnings
- Tests: `<command>` — baseline <n passed, m failed> → after <…>
- TDD proof: `python3 scripts/check_tdd.py` — every AC green with the change, red without
- Diff hygiene: `python3 scripts/check_diff_hygiene.py` — no unexplained suppressions or test changes

## Parallelization

<Which sessions/subagents can work in isolation, and how changes stay separated.>

- Each session/subagent has a functional name, a defined scope, and a visible report; no silent or unbounded background work.

## Build log

<Red evidence, per slice: the test, the failing output line, and why that failure was the
expected one (the behavior is missing — not a typo or an import path). Then the green run.>

## Review

<Filled during Review. Per round: reviewer lenses run; findings fixed (file:line → fix);
findings rejected with a one-line reason, so a later round does not re-raise them;
acceptance criteria with the evidence for each.>
