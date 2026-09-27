#!/usr/bin/env bash
set -e
source "$(dirname "$0")/../_fixtures/shop.sh"
cd app
git switch -qc feat/42-free-shipping
mkdir -p docs/changes/42
cat > src/shipping.py <<'PY'
FLAT_FEE = 5


def shipping_fee(order_total):
    """Shipping fee in dollars for an order total in dollars."""
    if order_total >= 100:
        return 0
    return FLAT_FEE
PY
cat >> tests/test_shipping.py <<'PY'


class FreeShippingTest(unittest.TestCase):
    def test_100_ships_free(self):
        self.assertEqual(shipping_fee(100), 0)

    def test_99_pays_the_fee(self):
        self.assertEqual(shipping_fee(99), 5)
PY
cat > docs/changes/42/plan.md <<'P'
# Free shipping from $100

- Task: shop/app#42 https://gitlab.example.com/shop/app/-/issues/42
- Path: Light
- Status: Approved

## Acceptance criteria

- AC-1: an order total of 100 or more pays 0 shipping
- AC-2: an order total under 100 still pays the flat 5

## Files that change

- src/shipping.py
- tests/test_shipping.py

## Proof

- AC-1: free from 100 — `python3 -m unittest tests.test_shipping.FreeShippingTest.test_100_ships_free`
- AC-2: fee below 100 — regression: `python3 -m unittest tests.test_shipping.FreeShippingTest.test_99_pays_the_fee`

## Test changes

## Review

### Round 1

- clean
P
git add -A && git commit -qm "feat: free shipping from 100 (Closes #42)"
git push -q -u origin feat/42-free-shipping
cd ..
cat > mrs/7.txt <<'M'
title:	feat: free shipping from 100
state:	open
source branch:	feat/42-free-shipping
target branch:	main
--
Closes #42

--- comments ---
reviewer (src/shipping.py:6): Why 100 and not 99.99? Is the boundary intended?
reviewer (src/shipping.py:6): Please extract 100 into a FREE_SHIPPING_THRESHOLD constant next to FLAT_FEE.
M
