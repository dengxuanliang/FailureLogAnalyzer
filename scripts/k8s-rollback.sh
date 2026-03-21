#!/usr/bin/env bash
# Roll back API and worker deployments one revision.
# Usage: ./scripts/k8s-rollback.sh [namespace]
set -euo pipefail

NAMESPACE="${1:-fla}"

echo "=== Current rollout history (${NAMESPACE}) ==="
for deploy in api worker-rule worker-llm frontend; do
  echo "--- ${deploy} ---"
  kubectl -n "${NAMESPACE}" rollout history "deployment/${deploy}"
done

read -rp "Roll back all deployments in ${NAMESPACE}? [y/N] " confirm
[[ "${confirm}" =~ ^[Yy]$ ]] || exit 0

for deploy in api worker-rule worker-llm frontend; do
  echo "Rolling back deployment/${deploy}..."
  kubectl -n "${NAMESPACE}" rollout undo "deployment/${deploy}"
done

echo "=== Waiting for rollback ==="
for deploy in api worker-rule worker-llm frontend; do
  kubectl -n "${NAMESPACE}" rollout status "deployment/${deploy}" --timeout=3m
done

echo "=== Rollback complete ==="
