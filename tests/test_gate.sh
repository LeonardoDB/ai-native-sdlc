#!/usr/bin/env bash
# Test suite for skills/ai-native-sdlc/assets/production-gate.sh.
# Usage: bash tests/test_gate.sh
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$REPO_ROOT/skills/ai-native-sdlc/assets/production-gate.sh"

pass=0
fail=0

# check <name> <expected-exit> <env-assignments...> -- <args...>
# env assignments like RELEASE_APPROVAL=REL-42 are passed as VAR=value.
check() {
  local name="$1" want="$2"
  shift 2
  local envs=()
  while [[ "$1" != "--" ]]; do envs+=("$1"); shift; done
  shift
  local out code
  out="$(env "${envs[@]}" bash "$GATE" "$@" 2>&1)"
  code=$?
  if [[ "$code" -eq "$want" ]]; then
    pass=$((pass + 1))
    echo "PASS: $name"
  else
    fail=$((fail + 1))
    echo "FAIL: $name (exit $code, want $want)"
    echo "      output: $out"
  fi
}

# --- must BLOCK (exit 2): production deploys without authorization ---
check "kubectl deploy --env=production" 2 -- "kubectl deploy --env=production"
check "terraform apply -target=module.production (was a bypass)" 2 -- "terraform apply -target=module.production"
check "helm upgrade prod-app (was a bypass)" 2 -- "helm upgrade prod-app"
check "kubectl apply -n prod -f deploy.yaml" 2 -- "kubectl apply -n prod -f deploy.yaml"
check "git push triggers no deploy gate when cmd is deploy+production word combo" 2 -- "make deploy production"

# --- must ALLOW (exit 0): not deploys, or read-only ---
check "cat docs/production-deploy.md (read, was a false positive)" 0 -- "cat docs/production-deploy.md"
check "undeploy production (word boundary)" 0 -- "undeploy production"
check "make deploy 2>&1 (no prod context)" 0 -- "make deploy 2>&1"
check "kubectl get pods -n production (read-only kubectl)" 0 -- "kubectl get pods -n production"
check "terraform plan -target=module.production (read-only terraform)" 0 -- "terraform plan -target=module.production"
check "helm list -n production (read-only helm)" 0 -- "helm list -n production"
check "grep -r deploy docs/production/" 0 -- "grep -r deploy docs/production/"
check "unrelated command" 0 -- "pip install requests"

# --- approval present: production deploy allowed ---
check "approved kubectl deploy (no expiry)" 0 RELEASE_APPROVAL=REL-42 -- "kubectl deploy --env=production"
check "approved helm upgrade (future expiry)" 0 RELEASE_APPROVAL=REL-42 RELEASE_APPROVAL_EXPIRY=2030-01-01T00:00:00Z -- "helm upgrade prod-app"
check "approved deploy with epoch expiry" 0 RELEASE_APPROVAL=REL-42 RELEASE_APPROVAL_EXPIRY=4102444800 -- "terraform apply -target=module.production"

# --- expired approval must BLOCK ---
check "expired ISO-8601 approval" 2 RELEASE_APPROVAL=REL-42 RELEASE_APPROVAL_EXPIRY=2000-01-01T00:00:00Z -- "kubectl deploy --env=production"
check "expired epoch approval" 2 RELEASE_APPROVAL=REL-42 RELEASE_APPROVAL_EXPIRY=1 -- "kubectl deploy --env=production"
check "unparseable expiry fails closed" 2 RELEASE_APPROVAL=REL-42 RELEASE_APPROVAL_EXPIRY=not-a-date -- "kubectl deploy --env=production"

# --- hook stdin mode (JSON payload, jq-style) ---
json_block="$(printf '{"tool_input":{"command":"kubectl deploy --env=production"}}' | RELEASE_APPROVAL='' bash "$GATE" 2>&1; echo "rc=$?")"
if [[ "$json_block" == *"BLOCK"* ]]; then
  pass=$((pass + 1)); echo "PASS: stdin JSON mode blocks without approval"
else
  fail=$((fail + 1)); echo "FAIL: stdin JSON mode (got: $json_block)"
fi
json_allow="$(printf '{"tool_input":{"command":"cat docs/production-deploy.md"}}' | RELEASE_APPROVAL='' bash "$GATE" 2>&1; echo "rc=$?")"
if [[ "$json_allow" == "ALLOW"* ]]; then
  pass=$((pass + 1)); echo "PASS: stdin JSON mode allows read-only"
else
  fail=$((fail + 1)); echo "FAIL: stdin JSON mode read-only (got: $json_allow)"
fi

echo
echo "gate: $pass passed, $fail failed"
[[ "$fail" -eq 0 ]]
