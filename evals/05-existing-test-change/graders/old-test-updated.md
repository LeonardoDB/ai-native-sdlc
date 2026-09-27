---
type: regex
target: {source: file, path: app/tests/test_shipping.py}
match: not_contains
---
shipping_fee\(20\), 5\)
