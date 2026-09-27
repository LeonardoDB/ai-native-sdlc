# The autonomous agent org

The org is an operating layer on top of the AI-native SDLC loop. It answers
three questions the loop alone leaves open: *who* the agents are, *how they
report and review each other*, and *where demand enters the system*. Agents
execute the same phases and gates as the base workflow; the org adds roles,
peer review, escalation, and intake so the loop runs with less human steering.

## Org model

Default roles, scaffolded by `scripts/init_org.py` and editable in
`org/org-chart.yaml`:

```text
CEO (human, owner)
 └── CTO (agent) — routes work, dispatches reviews, resolves conflicts
      ├── Product manager (agent) — first review of every intent
      ├── Product engineering agent (agent) — intake → tickets → intents
      └── Engineers (agents) — plan and build
           └── Reviewer (agent) — peer review when idle
```

Role cards live in `org/roles/*.md` and state in `org/status.yaml`. The status
file is the "who is busy" mechanism: an agent marks itself busy when it accepts
work and idle when it finishes; reviewers accept a review only when idle.
`scripts/org_status.py` performs those updates so the file stays validated:

```bash
python3 scripts/org_status.py status --json
python3 scripts/org_status.py agent engineer-1 busy --assignment "spec.md"
python3 scripts/org_status.py agent engineer-1 idle --last-report "spec approved"
python3 scripts/org_status.py review assign --id review-3 --artifact spec.md \
  --writer engineer-1 --reviewer reviewer-1
python3 scripts/org_status.py review submit --id review-3 \
  --verdict changes --evidence "https://github.com/org/repo/reviews/3"
python3 scripts/org_status.py review escalate --id review-4
```

## Reporting

1. Every agent commits its artifact (spec.md, plan.md, code+tests,
   review findings) with evidence.
2. Status changes ride in the same commit as the artifact they describe —
   the commit chain is the audit trail.
3. Reports flow up one level: engineers → CTO; PM/product → CTO; CTO → CEO.
   The CEO reads status and artifact commits at the gates and on escalation.

## Peer review

Writers never review their own work. When an artifact is finished, the writer
asks the CTO for a review; the CTO assigns an idle reviewer from
`org/status.yaml` (busy reviewers leave the request in the queue). The reviewer
writes `org/reviews/<artifact>-<id>.md` — severity-ranked findings with
evidence and a verdict (`approved` | `changes`) — and the writer addresses the
findings. Two unresolved rounds escalate to the CTO, then the CEO for
spec/plan conflicts.

Assignments, verdicts, rounds, and escalation are recorded through
`org_status.py review …` commands (never by hand-editing the status file), so
the CLI can enforce idle-reviewer assignment, no self-review, the two-round
limit, and consistent busy/idle states.

Review standards are the same as the base workflow: REVIEW.md passes (bugs,
security, compliance), evidence required, at most 5 nits per review.

## Human involvement

| Gate | Who decides |
|---|---|
| Intent | Product manager first; CEO on ambiguity |
| Spec / plan | Peer review; CEO after two unresolved disagreement rounds |
| PR merge | Human (CEO) |
| Release | Human (CEO) — production-gate.sh + gate ledger record |

The org is autonomous *within* the loop: agents generate, verify, review, and
report; humans hold the gates above. Nothing skips a gate when no human is
available — the loop pauses.

## Intake

Demand arrives through three channels and lands as versioned markdown records
in `org/intake/`:

- `github/` — `scripts/sync_issues.py pull` fetches open issues (idempotent;
  the state file tracks last-seen issue numbers per repo).
- `forms/` and `email/` — one markdown record per submission/message, same
  frontmatter format as GitHub records (source, record_id, received_at,
  author, priority).

Forms and email are ingested with `scripts/intake.py`:

```bash
python3 scripts/intake.py add --source form --record-id form-2026-091 \
  --author alice --priority high --summary "Export is missing" \
  --details-file /tmp/form-details.txt
python3 scripts/intake.py list --source email --status new
```

The product engineering agent consolidates records, files public feature
tickets with `scripts/sync_issues.py push`, and drafts tracker tasks in the
`assets/intent.md` shape. The PM reviews every task before it goes on the board
(a task on the board is an accepted intent).

## Escalation rules

- Intent ambiguity → PM → CEO.
- Spec/plan disagreement → writer ↔ reviewer (max 2 rounds) → CTO → CEO.
- Anything that would cross a gate without human approval → stop and report.

## Adoption

```bash
# 1. Scaffold the base workflow (if not already present)
python3 skills/ai-native-sdlc/scripts/init_workflow.py my-project --name "My idea" --git

# 2. Scaffold the agent org
python3 skills/ai-native-sdlc/scripts/init_org.py my-project

# 3. Configure GitHub intake
#    edit my-project/org/intake/config.json (repos, labels), then:
python3 my-project/scripts/sync_issues.py pull --dry-run

# 4. Commit and tell your agent to run the loop with the org
cd my-project && git add -A && git commit -m "scaffold agent org"
```

Run `sync_issues.py pull` on a schedule or in CI to keep the org fed; the
product engineering agent does the rest.

## Framework mapping

The org is framework-neutral, like the rest of the skill. Codex projects run
the role cards through Codex subagent configuration; Claude Code projects map
them to `.claude/agents/*.md`. The artifacts, protocol, and scripts are the
same either way.
