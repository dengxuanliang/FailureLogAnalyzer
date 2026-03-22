#!/usr/bin/env bash
# Apply a Kustomize overlay with pre-flight validation.
# Usage: ./scripts/k8s-apply.sh [dev|prod] [image_tag]
set -euo pipefail

OVERLAY="${1:-dev}"
IMAGE_TAG="${2:-latest}"
OVERLAY_DIR="k8s/overlays/${OVERLAY}"

if [[ ! -d "${OVERLAY_DIR}" ]]; then
  echo "Unknown overlay: ${OVERLAY}" >&2
  exit 1
fi

if [[ "${OVERLAY}" == "dev" ]]; then
  NAMESPACE="fla-dev"
else
  NAMESPACE="fla"
fi

echo "=== Pre-flight checks ==="
kubectl version --client
kubectl cluster-info

echo "=== Setting image tag: ${IMAGE_TAG} ==="
(cd "${OVERLAY_DIR}" && \
  kustomize edit set image \
    "ghcr.io/org/fla-api=ghcr.io/org/fla-api:${IMAGE_TAG}" \
    "ghcr.io/org/fla-frontend=ghcr.io/org/fla-frontend:${IMAGE_TAG}")

echo "=== Dry-run validation ==="
kubectl kustomize "${OVERLAY_DIR}" | kubectl apply --dry-run=server -f -

echo "=== Running migration ==="
./scripts/k8s-migrate.sh "${IMAGE_TAG}" "${NAMESPACE}"

echo "=== Applying manifests ==="
kubectl kustomize "${OVERLAY_DIR}" | kubectl apply -f -

echo "=== Waiting for rollout ==="
kubectl -n "${NAMESPACE}" rollout status deployment/api --timeout=5m
kubectl -n "${NAMESPACE}" rollout status deployment/worker-rule --timeout=5m
kubectl -n "${NAMESPACE}" rollout status deployment/worker-llm --timeout=5m
kubectl -n "${NAMESPACE}" rollout status deployment/frontend --timeout=5m

echo "=== Post-apply health check ==="
API_IP=$(kubectl -n "${NAMESPACE}" get svc api -o jsonpath='{.spec.clusterIP}')
kubectl -n "${NAMESPACE}" run tmp-health-check --image=curlimages/curl --rm -i --restart=Never -- \
  curl -sf "http://${API_IP}:8000/api/v1/health"

echo "=== Deploy complete ==="
