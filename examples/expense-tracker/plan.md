# Expense tracker self-service — Build Plan

- Derived from: spec.md (commit d4e5f6a)
- Status: Approved
- Date: 2026-08-21

## Files that change

- `portal/src/expenses/ExpenseForm.tsx` (new)
- `portal/src/expenses/StatusPanel.tsx` (new)
- `claims-api/routes/expenses.py` (new)
- `claims-api/services/policy_engine.py` (new)
- `claims-api/tests/test_expenses.py` (new)

## Order of work

1. Add the submit endpoint behind existing SSO.
2. Add the policy engine with the four claim states.
3. Build the form and status panel against the endpoints.
4. Wire the nightly export job.

## Risks

- An ERP export format change would block the release — pin the format and put the export job behind a feature flag.
- Policy rule conflicts were resolved in spec; comment the exception where it lives in code.

## Proof

- `test_expenses.py` covers the four claim states and the export mapping.
- Screenshot of the status panel matches the approved mock.

## Verification

- `make build` ends with "Build succeeded".
- `make test` all green.
- `make lint` zero warnings.

## Parallelization

- Session 1 (api): claims-api files.
- Session 2 (portal): portal/src/expenses files.
- Each session named for its function, separate worktree, reports what it ran and what it saw.
