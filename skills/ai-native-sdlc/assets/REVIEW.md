# Review standards

Applies to agentic review passes. Evidence before opinions.

## Passes

An independent reviewer (a fresh-context subagent) runs three lenses — one
reviewer with all three for a small diff — and tags each finding with its lens:

- Correctness: logic errors, broken edge cases, subtle regressions
- Spec + conventions: the change matches spec.md, plan.md, our design principles,
  and the repo's conventions
- Simplicity + security: needless complexity; injection risks, authentication gaps,
  PII in logs

Every finding carries file:line, severity, and confidence; the coordinating agent
keeps those at confidence 80+ and checks lower-confidence high-severity ones in the
code before keeping or dropping them.

## What Important means here

Reserve Important for findings that would break behavior, leak data, or breach a policy. Style and naming are nits.

## Cap the nits

Report at most five nits per review; summarize the rest as a count.

## Do not report

Generated files under src/gen/ and anything CI already enforces.

## Human review

Findings do not approve or block on their own; branch protection requires code owner approval. Humans answer two questions:

1. Is this the change the plan intended?
2. Is the risk acceptable?

Line-by-line human review is reserved for regulated and critical-path code.
