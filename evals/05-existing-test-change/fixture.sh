#!/usr/bin/env bash
set -e
source "$(dirname "$0")/../_fixtures/shop.sh"
task 43 "Raise the flat shipping fee to \$7" <<'T'
Carrier costs went up: the flat shipping fee becomes $7 for every order.

Acceptance criteria
- Every order pays a shipping fee of 7.
T
