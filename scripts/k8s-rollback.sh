#!/usr/bin/env bash
# Roll back all app deployments one revision.
# Usage: ./scripts/k8s-rollback.sh [namespace]
set -euo pipefail

NAMESPACE="${1:-fla}"
DEPLOYMENTS=(api worker-default worker-rule worker-llm frontend)

command -v kubectl >/dev/null 2>&1 || {
  echo "Missing required command: kubectl" >&2
  exit 1
}

echo "=== Current rollout history (${NAMESPACE}) ==="
for deploy in "${DEPLOYMENTS[@]}"; do
  echo "--- ${deploy} ---"
  kubectl -n "${NAMESPACE}" rollout history "deployment/${deploy}"
done

read -rp "Roll back all deployments in ${NAMESPACE}? [y/N] " confirm
[[ "${confirm}" =~ ^[Yy]$ ]] || exit 0

for deploy in "${DEPLOYMENTS[@]}"; do
  echo "Rolling back deployment/${deploy}..."
  kubectl -n "${NAMESPACE}" rollout undo "deployment/${deploy}"
done

echo "=== Waiting for rollback ==="
for deploy in "${DEPLOYMENTS[@]}"; do
  kubectl -n "${NAMESPACE}" rollout status "deployment/${deploy}" --timeout=3m
done

echo "=== Rollback complete ==="
