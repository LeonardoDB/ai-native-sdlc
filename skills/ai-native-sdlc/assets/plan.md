# <Title> — Build Plan

- Derived from: spec.md <commit or path>
- Status: Draft | Approved
- Date: <YYYY-MM-DD>

## Files that change

<One path or glob per bullet — no prose. Examples:>

- src/main.py
- tests/test_main.py

## Order of work

1. <Step with concrete commands where relevant>

## Risks

<What could go wrong and how we de-risk it; e.g., "the claims-core API rate-limits at 50 rps; the panel must cache.">

## Proof

<The tests that prove the change, and the visual evidence where relevant; e.g., "test_status.py covers the four claim states; screenshot matches the approved mock.">

## Verification

<Commands to run and what healthy output looks like; e.g., `make build` ends with "Build succeeded", `make test` with all green.>

## Parallelization

<Which sessions/subagents can work in isolation, and how changes stay separated.>

- Each session/subagent has a functional name, a defined scope, and a visible report; no silent or unbounded background work.
