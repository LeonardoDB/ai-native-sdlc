# Review standards

Applies to agentic review passes. Evidence before opinions.

## Passes

Run three passes and tag each finding with its pass:

- Bugs: logic errors, broken edge cases, subtle regressions
- Security: injection risks, authentication gaps, PII in logs
- Compliance: the change matches spec.md, plan.md, and our design principles

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
