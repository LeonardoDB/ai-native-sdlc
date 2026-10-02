# Autonomy — running the loop without stopping at each gate

By default every gate waits for the user. In **delegated** mode the agent
passes the routine ones itself and records what it decided, so a run can go
from the task link to an opened draft MR/PR with nobody watching. The user
reviews the MR/PR instead of each step, so everything the agent decided
alone has to be visible there.

## Turning it on

CLAUDE.md's `## Autonomy` section, or the user saying so for one run
("run this autonomously"; "ask me this time" turns it off for one run):

```markdown
## Autonomy

- Mode: delegated
- Priorities: <optional — what wins when routine choices conflict, e.g. "simple over complete; no new dependencies">
- Extra escalations: <optional — decisions that always go to the user, e.g. "anything touching billing">
```

Without the section, the mode is `ask` and nothing below applies.

## What changes

| Step | `ask` (default) | `delegated` |
|---|---|---|
| Workspace | propose the branch, wait | create it; a dirty tree still stops |
| Design | questions go to the user | answered by the agent and recorded (below) |
| Spec and plan gates | the user approves | the agent approves once its own interrogation passes |
| Shape | the architect decides; two failed rounds go to the user | the same, but two failed rounds escalate |
| Review | two failed rounds go to the user | the same, but two failed rounds escalate |
| Deliver | ask once, then open the MR/PR | commit, push, and open it **as a draft**, without asking |

Nothing else moves. The checks and `hooks/gate.py` still block merging,
pushing to the default branch, and publishing with failing checks.

## Answering open questions

Answer each question from, in this order: the task, the knowledge stores
(`references/knowledge.md`), the code, then the web for market or product
questions (how other products handle it, what users expect). Cite the source
of each answer. Take the recommendation you would otherwise have put to the
user, guided by the `Priorities` line.

Record each one under `## Assumptions (delegated)` in spec.md (plan.md on the
light path), one line each:

```markdown
- <question> → <answer taken> — <why> [<source>]
```

An answer with no source is the agent's own reasoning; say so (`[own judgment]`).

## Escalate instead

Stop and ask — never decide — when a question or a gate touches:

- a change that is hard to undo: a schema or data migration, a public API or
  contract other services use, a shared write path
- a scope change users would notice: the task asks for one thing, the
  answer means building another
- auth, secrets, payments, or personal data
- a conflict with a decision recalled from the knowledge stores
- a question you cannot answer with a recommendation (a real 50/50, or an
  unknown that changes the design)
- anything CLAUDE.md lists under `Extra escalations`
- the architect or the review not converging in two rounds

To escalate: leave the artifact `Status: Draft`, write the question under its
`## Open questions` with your recommendation and the options, and stop with
the question as the last message. Nothing is committed or pushed. The next
run with the same link resumes at the same gate (`state.next`), and the user's
answer is recorded as theirs.

## Recording a delegated approval

Write `Status: Approved` as usual, and add the line under it:

```markdown
- Status: Approved
- Approved-by: delegated (<YYYY-MM-DD>)
```

An approval the user gave is `Approved-by: <user>`. The checks only read
`Status`; `Approved-by` is for the people reviewing the MR/PR.

## In the MR/PR

The body gets a `## Delegated decisions` section: each assumption from spec.md
and plan.md, each gate the agent approved, and anything it rejected in Shape or
Review. The MR/PR stays a draft; marking it ready is the user's call after
reading it.

## Running it unattended

The skill does not schedule itself. Start a run from a terminal or a CI job:

```bash
claude -p "Run the ai-native-sdlc workflow for <task link>" \
  --permission-mode acceptEdits --allowedTools "Bash Edit Write Read Agent Skill"
```

Keep `hooks/gate.py` wired (the plugin does it); it is what keeps an
unattended run from merging or publishing failing work.
