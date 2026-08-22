# Graph engineering — the loop as a directed graph

The AI-native SDLC is a directed graph, not a linear pipeline. Treating it as a graph is what makes the loop automatable, auditable, and parallelizable.

## Node types

- **Plays** — the work units: capture intent, requirements and design, plan mode, build, continuous evals, PR review, hooks, CI/CD, closing the loop.
- **Artifacts** — the committed evidence each play produces: intent.md, spec.md, plan.md, the diff and its tests, the PR with its review findings, the incident record.
- **Gates** — human judgment points where an artifact is accepted, approved, or rejected. Gates are the only nodes automation may never skip.
- **Triggers** — directed edges that fire the next play when a gate passes: an accepted intent fires Design; an approved spec fires plan mode; a merged PR fires the pipeline; a breached control band writes the next intent.

## The runtime loop

intent.md → (accepted) → spec.md → (approved) → plan.md → (approved) → code + tests → (PR merged) → release → (authorized) → monitoring → (band breach) → new intent.md → back to the start.

The machine-readable form ships in `assets/workflow-graph.example.yaml`.

## The adoption graph

The plays also form a dependency graph for adoption, separate from the runtime order. Start at a leaf play — nothing points into it: capture intent, CLAUDE.md, feedback loop, build-time hooks, plan mode. Then adopt the plays that depend on them: skills, subagents, continuous evals; then requirements and design and PR review; then CI/CD and approval gates; and finally close the loop. Adopting in this order means every new play arrives with its prerequisites already in place.

## Why graph engineering matters

- **Automation.** Each accepted artifact fires the next gate mechanically. The end state is a loop in which no human starts a stage by hand — they review what the agent flagged at the gates.
- **Parallelism.** Independent branches of the graph run concurrently in separate worktrees; the graph shows where work can split and where it must join before a gate.
- **Audit.** Node history is the record: every artifact commit, gate decision, and trigger is attributable to a person or a run.
- **Observability.** The graph's current state — what is in flight, what is blocked at which gate — is the team's shared view of the pipeline.

## Guardrails

- Edges may automate everything up to a gate; gates themselves remain human.
- The production gate is terminal for agents: release authorization is a hook-enforced edge, not an advisory one.
- When encoding the graph for automation, keep gate nodes explicit and version the graph alongside the artifacts it describes.
- Subagent and session nodes follow the same rules as plays: named for their function, visible to the developer, bounded, and evidence-reporting.
