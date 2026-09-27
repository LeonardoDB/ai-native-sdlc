# <Change title>

## Change

<One paragraph: what changed and why.>

## Implements

- task: <task ref + link> (Closes group/project#42 · Fixes ENG-123)
- spec: docs/changes/<task>/spec.md (full path only)
- plan: docs/changes/<task>/plan.md

## Files

<Files changed — must match plan.md "Files that change", or plan.md was
updated in this same MR/PR.>

## Acceptance criteria

- [ ] <criterion from the task> — <evidence: test, walkthrough, screenshot>

## Evidence (verified before requesting review)

- [ ] Build: <paste output>
- [ ] Typecheck: <paste output>
- [ ] Tests: <paste output> (baseline before the change: <…>)
- [ ] Lint: <paste output>
- [ ] TDD proof (`check_tdd.py`): <each AC green with the change, red without>
- [ ] Diff hygiene (`check_diff_hygiene.py`): <clean, or the reasons given>
- [ ] Screenshot matches the approved mock (UI changes)

## Review (REVIEW.md, independent reviewer)

- [ ] Correctness · [ ] Spec + conventions · [ ] Simplicity + security
- Rounds: <n>; findings fixed and rejected are in plan.md `## Review`

## Notes

<Nits count, skipped generated paths, open questions. Keep to the 5-nit cap.>
