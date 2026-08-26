# Gate ledger

Every gate decision — intent acceptance, spec approval, plan approval, PR
merge, **release authorization**, on-call triage — is a record in
`ledger.jsonl` (one JSON object per line). Records are hash-chained
(`prev_hash`/`hash`), so the ledger is append-only by construction: any edit
to a past record breaks the chain and fails `verify`.

The release gate hook accepts `RELEASE_APPROVAL=ledger:<record-id>` and
verifies the record before allowing a production deploy.

## Record an approval

```bash
python3 scripts/gate_ledger.py record \
  --gate release_authorization \
  --artifact "deploy app v1.2.3 to production" \
  --commit cf13ec7 \
  --approver "Ada (release manager)" \
  --evidence "INC-42 / REL-2026-08-26" \
  --expires-at 2026-08-27T12:00:00Z
git add gates/ledger.jsonl && git commit -m "gates: record release authorization REL-…"
```

- `--gate` uses the gate names from `workflow-graph.yaml` (e.g.
  `product_owner_accept`, `release_authorization`, `on_call_triage`).
- `--expires-at` is optional (ISO-8601 UTC or epoch seconds); a release
  authorization that should not outlive the deploy window should set it.
- The record is only *authoritative* once **committed**: `verify
  --require-committed` (what the gate hook uses) rejects uncommitted ledgers.

## Verify

```bash
python3 scripts/gate_ledger.py verify --record release_authorization-001 \
  --require-committed --graph workflow-graph.yaml --require-gates
```

- `--require-committed` — fail unless the ledger is committed and clean.
- `--graph … --require-gates` — fail unless every gate in the workflow graph
  has at least one recorded decision (governance completeness check).

## Tamper detection

`verify` replays the chain: every record's `hash` must match its content and
each `prev_hash` must point at the previous record. Rewriting history (e.g.
changing an approver after the fact) is detected immediately. This is
evidence-grade provenance for compliance: *who approved what, when, with what
evidence* — queryable instead of implicit.
