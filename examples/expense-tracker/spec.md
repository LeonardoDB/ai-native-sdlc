# Expense tracker self-service — Specification

- Derived from: intent/intent.md (commit a1b2c3d)
- Author: A. Chen + agent
- Status: Approved
- Date: 2026-08-21

## Requirements

### Functional

- Submit an expense with amount, date, category, receipt image, and optional note.
- Policy engine evaluates each receipt against the rule set, distinguishing non-negotiable and advisory rules.
- Status visible to the submitter: draft, submitted, in review, approved, rejected, paid.
- Approver queue sorted by age with flagged violations.

### Non-functional

- Existing SSO only; no new PII in session data.
- ERP export format unchanged.
- p95 latency under 500 ms for submit and status endpoints.

## Design

- Web app: `portal/src/expenses/` (React); API: `claims-api/routes/expenses.py` (FastAPI); policy engine as a library.
- Data flow: submit → validate → policy rules → status store → approver queue; nightly export job to ERP.
- Interfaces: `POST /expenses`, `GET /expenses`, `GET /expenses/{id}/status`; export job reads the status store.

## Standards applied

- Security skill: SSO enforced; receipt images stripped of EXIF metadata before storage.
- UX skill: status and next step visible without opening the report.

## Gotchas

- Policy conflict: "meals over $75 require an itemized receipt" versus "scanned receipts only" — escalated to the policy owner; decision: itemized photos accepted as PDF attachment in v1.
- ERP export is weekly and scheduled; paid status may lag by up to a day.

## Open questions

- Bulk upload deferred to v2 (owner: A. Chen).

## Verification plan

- Unit tests for the policy engine covering all six statuses and their transitions.
- Integration test for submit → status.
- Screenshot of the status panel matches the approved mock.
