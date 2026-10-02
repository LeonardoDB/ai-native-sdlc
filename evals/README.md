# Evals

Behavioral evals for the skill, run with Claude Code's native runner:

```bash
# every case (the end-to-end ones run a full task — budget accordingly)
claude plugin eval . --scaffold --trust-plugin --no-publish --allow-tools Bash Edit Write

# one case, one run, capped
claude plugin eval . --scaffold --trust-plugin --no-publish --allow-tools Bash Edit Write \
  --case '01-*' --runs 1 --max-cost-usd 5

# the cheap gate and negative cases, on a small model
claude plugin eval . --scaffold --trust-plugin --no-publish --allow-tools Bash Edit Write \
  --tag gate --tag negative --model haiku
```

**macOS:** inside the runner's sandbox, `/usr/bin/git` (the Xcode `xcrun` shim)
fails with `couldn't create cache file … Operation not permitted`, so every
case that uses git breaks. Install a standalone git ahead of it on PATH
(`brew install git`); Linux and CI are unaffected.

A case that expects the agent to reach a later gate must approve the earlier
ones in its prompt — the workflow stops at every gate, starting with the
branch proposal in Workspace.

`--allow-tools Bash Edit Write` is required — without it the runner denies those
tools and the agent cannot work. `--scaffold` is required too: each case's `fixture.sh` builds the workspace (it
sources `_fixtures/shop.sh`, which you can read — it runs as you). Results go
to `evals/results/` (git-ignored). Cases run a real agent on your credential;
use `--max-cost-usd` to cap a run.

The fixture is offline: `app/` is a Python repo whose GitLab origin pushes to
a local bare repo, and `app/bin/glab` stands in for the GitLab CLI, serving
tasks and MRs from files and logging every call to `tracker.log`. Graders are
deterministic where they can be — the files the agent wrote, the tracker log,
the trace (`check_tdd: … 0 failure(s)` means the TDD proof passed) — and an
LLM rubric only where judgment is the point.

By default each case also runs without the plugin (`--ablation with-without`)
and reports the score delta — the evidence that the skill, not the model alone,
produces the behavior. `--ablation none` halves the cost while iterating.

Measured so far (haiku, one run each): `03-board-link-rejected` 1.00,
`08-neg-explain` 1.00. `09-kb-recall` 0.33 on its first design, which
expected a spec without approving the branch first — the agent correctly
stopped at Workspace; the prompt now approves the branch. The end-to-end
cases have not been run yet (they need the git fix above on macOS).
`12-delegated-escalates` 1.00 (session model, one run, after fixing its
`never-pushed` grader). `11-delegated-to-draft-mr` 1.00 on two of three runs;
the first stopped before the MR (0.63) and kept no transcript.

| Case | Checks |
|---|---|
| 01-task-to-mr | the whole loop: plan maps every AC, slices dispatched to the builder, red proven, checks green, MR opened with the closing keyword, task never edited, never merged |
| 02-waits-for-plan-approval | without pre-approval it stops at the plan: no code, no push, no MR |
| 03-board-link-rejected | a board link gets a request for the task link, not work |
| 04-dirty-tree-stops | someone else's uncommitted change stops the run and survives it |
| 05-existing-test-change | a behavior change that breaks an existing test lists it under Test changes |
| 06-mr-feedback | a review round: the requested change made, the question answered, replies posted, no merge |
| 07-bug-root-cause | a bug: reproduction test first, root cause in the plan, the boundary fixed |
| 08-neg-explain | a plain question does not start the workflow |
| 09-kb-recall | Design recalls an ADR the code does not show (money is Decimal) and the spec cites and follows it |
| 10-shape-architect | Build's Shape step: stubbed types and signatures, the architect dispatched, its verdict recorded in plan.md, and no test written before it |
| 11-delegated-to-draft-mr | `## Autonomy: delegated`, nobody answering: the routine question answered under Assumptions (delegated), the gates recorded `Approved-by: delegated`, TDD proof green, a draft MR with a Delegated decisions section, never merged |
| 12-delegated-escalates | delegated mode still stops on a public-API change (the fee's unit): it asks, with a recommendation; no code, no push, no MR |
