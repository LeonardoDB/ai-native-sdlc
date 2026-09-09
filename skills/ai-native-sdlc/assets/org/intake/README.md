# Intake — where demand enters the org

Every demand lands here as a markdown record, no matter the channel. The
product engineering agent reads these, consolidates them into feature tickets,
and drafts `intent.md` for PM review.

## Channels

- `github/` — issues pulled by `scripts/sync_issues.py pull`
  (one file per issue, named `<repo>-<number>.md`)
- `forms/` — user feedback from app forms (one file per submission)
- `email/` — feedback and complaints from email (one file per message)

`scripts/intake.py` writes the form/email records:

```bash
python3 scripts/intake.py add --source form --record-id form-001 \
  --author alice --priority high --summary "Export is missing." \
  --details-file /tmp/form-details.txt
python3 scripts/intake.py add --source email --record-id email-2026-001 \
  --author bob --summary "Cannot upload receipts."
python3 scripts/intake.py list --source form --status new
```

Record ids must be unique across the intake queue and match
`[A-Za-z0-9._-]+`; paths are validated to stay inside `org/intake/`.

## Record format (all channels)

```markdown
---
source: github|form|email
record_id: unique id (issue number, form id, message id)
received_at: ISO-8601 UTC
author: who reported it (when known)
priority: low|normal|high
---

## Summary
One or two sentences: what the user cannot do today.

## Details
Anything that makes the demand concrete: steps, screenshots, expectations.

## Status
new | triaged | ticket_filed | intent_drafted | done
```

## GitHub config

`config.json` next to this README drives `sync_issues.py pull` (repo list,
label filter, state file). See `scripts/sync_issues.py --help`.
