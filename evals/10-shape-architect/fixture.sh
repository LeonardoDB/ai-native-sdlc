#!/usr/bin/env bash
set -e
source "$(dirname "$0")/../_fixtures/shop.sh"
task 46 "Discount codes at checkout" <<'T'
An order can carry one discount code. A code is either a percentage off the
order total (1 to 100) or a fixed amount off, never both. The discount never
takes the total below 0.

Acceptance criteria
- A 10% code on an order of 200 gives a total of 180.
- A fixed 15 code on an order of 40 gives a total of 25.
- A fixed 50 code on an order of 30 gives a total of 0.
- A code of 0% or above 100% is rejected.
T
