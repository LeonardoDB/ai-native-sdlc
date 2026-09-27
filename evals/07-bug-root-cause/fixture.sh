#!/usr/bin/env bash
set -e
source "$(dirname "$0")/../_fixtures/shop.sh"
cd app
cat > src/shipping.py <<'PY'
FLAT_FEE = 5


def shipping_fee(order_total):
    """Shipping fee in dollars for an order total in dollars."""
    if order_total > 100:
        return 0
    return FLAT_FEE
PY
git add -A && git commit -qm "feat: free shipping over 100"
git push -q origin main && git update-ref refs/remotes/origin/main HEAD
cd ..
task 44 "Bug: an order of exactly \$100 is charged \$5 shipping" <<'T'
A customer with an order total of exactly $100 was charged $5 shipping. Our
policy is free shipping from $100.

Acceptance criteria
- An order total of exactly 100 pays 0 shipping.
- An order total under 100 still pays the flat 5.
T
