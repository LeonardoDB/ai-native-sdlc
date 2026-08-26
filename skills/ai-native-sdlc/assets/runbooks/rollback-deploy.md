# Runbook: rollback a deployment

The route named by `bands.yaml` (`runbook:rollback-deploy`). The rollback path
is the most rehearsed path in the system — Phase 6 (Maintain) calls it first
when a control band breaches inside a deploy window.

## When to run

- A control band breached within the deploy window (e.g. `post_deploy_5xx_rate`
  at 3σ) with a deployment in that window.
- A user-reported regression traceable to the latest release.

## Pre-requisites

- The rollback is rehearsed in staging at least monthly.
- The previous release is known to be healthy (its own post-deploy metrics and
  eval suite were green).

## Steps

1. **Confirm the affected release and its commit.**
   `<how to find in your platform, e.g. gh release view / helm history / git log -1 --oneline>`
2. **Verify the previous release is healthy.**
   `<checks: metrics back at baseline, evals pass>`
3. **Execute the rollback.**
   `<the exact command for your platform — one command, rehearsed>`
4. **Verify the rollback.**
   `<checks: the band is back at baseline, traffic is served>`
5. **Record the execution.** Release authorization reference + incident number
   (gate ledger / `gates/`, `INC-<n>`).
6. **Write the diagnosis back** as `intent/intent.md` so the fix re-enters the
   pipeline at Plan, and add an eval for the incident class.

## Who may run

- On-call engineer, with the release authorization recorded
  (`RELEASE_APPROVAL` + `RELEASE_APPROVAL_EXPIRY` in the gate hook, or the
  org's approval service).
- Automation may trigger this runbook only via the gated route in `bands.yaml`
  (3σ `propose`), never directly.

## Test / rehearsal

```bash
<command to rehearse in staging>
```

- Expected outcome: `<healthy output, e.g. "Rollback succeeded; band back at baseline">`
- Rehearse after every deploy-path change and at least monthly.

## Post-incident

- Add an eval for the incident class (`evals/<name>.json`).
- If the band was noise, tune `bands.yaml` — dismissals reduce future noise.
