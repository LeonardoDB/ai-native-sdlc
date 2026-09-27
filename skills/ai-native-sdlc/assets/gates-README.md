# Gate ledger

Every gate decision — the task taken from the board, spec approval, plan
approval, MR/PR merge — is a record in `ledger.jsonl` (one JSON object per
line). Records are hash-chained
(`prev_hash`/`hash`), so the ledger is append-only by construction: any edit
to a past record breaks the chain and fails `verify`.

(Optional extra: the release gate hook `production-gate.sh`, not scaffolded,
accepts `RELEASE_APPROVAL=ledger:<record-id>` and verifies the record before
allowing a production deploy.)

## Record an approval

```bash
python3 scripts/gate_ledger.py record \
  --gate engineer_approve \
  --artifact plan.md \
  --commit cf13ec7 \
  --approver "Ada (tech lead)" \
  --evidence "group/project#42"
git add gates/ledger.jsonl && git commit -m "gates: record plan approval for group/project#42"
```

- `--gate` uses the gate names from `workflow-graph.yaml` (`tracker_board`,
  `product_owner_approve`, `engineer_approve`, `code_owner_approve`).
- `--expires-at` is optional (ISO-8601 UTC or epoch seconds).
- The record is only *authoritative* once **committed**: `verify
  --require-committed` rejects uncommitted ledgers.

## Verify

```bash
python3 scripts/gate_ledger.py verify --record engineer_approve-001 \
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
