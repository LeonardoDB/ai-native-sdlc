# Debugging a bug task

A bug task follows the same loop — workspace, plan, approval, red → green,
review, MR/PR — but Build starts from evidence instead of a design. The goal
is the root cause, proven by a test, not a patch that makes the symptom go
away. Most bugs take the light path (plan.md only); a bug whose fix changes
behavior users rely on takes the full path.

## 1. Reproduce before anything else

- Turn the report into a **failing test at the public interface** that shows
  the reported symptom. Run it and confirm it fails the way the report says —
  that is the red of this task, recorded in plan.md's Build log.
- Cannot reproduce? Stop and report what you tried (inputs, environment,
  versions, the commands and their output). Guessing a fix for a bug you
  cannot see ships a second bug.
- A flaky reproduction is a finding: note the rate (e.g. 3 of 20 runs) and
  what varies (order, time, concurrency).

## 2. Evidence, not intuition

- Read the actual failure: the full stack trace, the logs around it, the
  input that triggers it.
- Find what changed: `git log -p --follow -- <file>`, `git log -S '<snippet>'`,
  `git blame -L <range> <file>` on the suspect lines, and `impact_map.py
  --files <file>` for how risky and how often fixed the area is.
- When a known-good version exists, bisect it with the reproduction:
  `git bisect start <bad> <good> && git bisect run <repro command>`. The first
  bad commit usually names the cause.

## 3. Hypotheses, one variable at a time

- Write the candidate causes in plan.md's Build log, ranked, each with the
  observation that would confirm or refute it.
- Test one hypothesis at a time and change one thing at a time. Revert what
  did not confirm it before trying the next.
- Keep going until one hypothesis explains **every** observation, not just
  the headline one.

## 4. Root cause, then the plan

- State the root cause in plan.md with `file:line`, and why the existing
  tests did not catch it.
- The plan names the minimal fix and the regression test (the reproduction
  from step 1). A fix waits for the plan's approval like any other change —
  a bug report that says "just fix it" still gets a plan.
- A symptom fix (catching the exception, clamping the value, a retry) is not a
  root-cause fix; if it is the right trade-off, say so in the plan as a
  Deviation with the reason.

## 5. Fix, prove, review

- Red → green with the reproduction test; `check_tdd.py` proves it fails
  without the fix and `check_mutations.py` that the fixed lines are guarded.
- Look for siblings: the same mistake elsewhere (`git grep` the pattern). Fix
  them in this task only if the plan says so; otherwise propose a follow-up.
- In the MR/PR body, name the root cause and, when bisect or blame found it,
  the commit that introduced it. A comment on the task goes only with the
  user's confirmation.
