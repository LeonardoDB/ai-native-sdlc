#!/usr/bin/env bash
set -e
source "$(dirname "$0")/../_fixtures/shop.sh"
task 42 "Free shipping from \$100" <<'T'
Orders of $100 or more should ship free. Below that, keep the flat $5 fee.

Acceptance criteria
- An order total of 100 or more pays 0 shipping.
- An order total under 100 still pays the flat 5.
T
