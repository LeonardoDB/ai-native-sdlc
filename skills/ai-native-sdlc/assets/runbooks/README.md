# Runbooks

Runbooks are the **pre-approved action paths** the Maintain phase may trigger:
a 3σ `propose` route in `bands.yaml` names a runbook, and the agent may
execute that runbook without a person in the invocation path — the human gate
is the review of the resulting PR or incident record.

Each runbook must:

- have an owner and a rehearsed test in staging (rollback: at least monthly);
- name the exact commands and their healthy output, so execution is
  deterministic and verifiable;
- record its execution and any release authorization it consumed;
- convert anything larger than a small bounded fix into `intent.md`.

Ship `rollback-deploy.md` first — rollback is the most rehearsed path because
Phase 6 calls it before any other.

Add your own runbooks (e.g. `quarantine-flaky-test.md`, `drain-and-restart.md`)
the same way, and reference them from `bands.yaml` routes.
