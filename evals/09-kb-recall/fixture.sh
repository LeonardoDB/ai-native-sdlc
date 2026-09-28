#!/usr/bin/env bash
set -e
source "$(dirname "$0")/../_fixtures/shop.sh"
cd app
mkdir -p docs/adr
cat > docs/adr/0001-money-is-decimal.md <<'MD'
# 0001 — Money is Decimal, never float

- Status: Accepted

## Decision

Every money amount — prices, order totals, fees, thresholds — is a
`decimal.Decimal` in code and in comparisons. Never a float, never a float
literal in a money comparison (`Decimal("100")`, not `100.0`).

## Why

INC-12 (2025): a float comparison charged shipping on orders of exactly
$100.00 because the total summed to 99.99999999. Customers were refunded.
MD
cat >> CLAUDE.md <<'MD'

## Knowledge base

- decisions — why the system is the way it is (ADRs) — repo `docs/adr/` — anyone, via the MR
MD
git add -A && git commit -qm "docs: ADR 0001 money is Decimal"
git push -q origin main && git update-ref refs/remotes/origin/main HEAD
cd ..
task 45 "Free shipping from \$100" <<'T'
Orders of $100 or more should ship free. Below that, keep the flat $5 fee.

Acceptance criteria
- An order total of 100 or more pays 0 shipping.
- An order total under 100 still pays the flat 5.
T
