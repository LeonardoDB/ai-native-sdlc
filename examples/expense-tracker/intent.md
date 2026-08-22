# Expense tracker self-service

- Author: A. Chen (finance ops)
- Source: finance-ops Slack #tooling-ideas
- Status: Accepted
- Date: 2026-08-20

## Problem

Employees submit expense reports by emailing PDFs to finance. Approvers spend roughly a third of their time matching receipts to policy rules by hand, and employees can't see where a report stands.

## Proposed outcome

Employees submit expenses in a web app; the app applies policy rules and shows status, next step, and expected date. Approvers see a prioritized queue with policy violations flagged.

## Affected users and systems

Employees, approvers, finance ops; expense policy documents; existing payroll/ERP export integration.

## Constraints

No new PII beyond existing payroll data. Existing SSO only. Must export in the current ERP format. Mobile-first is out of scope.

## Out of scope

Corporate card reconciliation, per-diem automation, native mobile app.

## Open questions

Should bulk receipt upload be supported in v1? Which policy rules are non-negotiable versus advisory?
