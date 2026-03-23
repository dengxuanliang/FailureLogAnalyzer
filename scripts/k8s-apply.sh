#!/usr/bin/env bash
# Apply a Kustomize overlay with image overrides, migration, and rollout checks.
# Usage: ./scripts/k8s-apply.sh [dev|prod] [image_tag]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

OVERLAY="${1:-dev}"
IMAGE_TAG="${2:-latest}"
OVERLAY_DIR="${REPO_ROOT}/k8s/overlays/${OVERLAY}"

if [[ ! -d "${OVERLAY_DIR}" ]]; then
  echo "Unknown overlay: ${OVERLAY}" >&2
  exit 1
fi

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

require_cmd kubectl
require_cmd ruby
require_cmd cp

if [[ "${OVERLAY}" == "dev" ]]; then
  NAMESPACE="fla-dev"
  DEFAULT_API_IMAGE_REPO="localhost:5000/fla-api"
  DEFAULT_FRONTEND_IMAGE_REPO="localhost:5000/fla-frontend"
else
  NAMESPACE="fla"
  DEFAULT_API_IMAGE_REPO="ghcr.io/org/fla-api"
  DEFAULT_FRONTEND_IMAGE_REPO="ghcr.io/org/fla-frontend"
fi

API_IMAGE_REPO="${API_IMAGE_REPO:-${DEFAULT_API_IMAGE_REPO}}"
FRONTEND_IMAGE_REPO="${FRONTEND_IMAGE_REPO:-${DEFAULT_FRONTEND_IMAGE_REPO}}"
API_IMAGE="${API_IMAGE_REPO}:${IMAGE_TAG}"

render_kustomize() {
  if kubectl kustomize --help >/dev/null 2>&1; then
    kubectl kustomize "$1"
    return
  fi

  if command -v kustomize >/dev/null 2>&1; then
    kustomize build "$1"
    return
  fi

  echo "Neither 'kubectl kustomize' nor 'kustomize' is available." >&2
  exit 1
}

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

cp -R "${OVERLAY_DIR}/." "${TMP_DIR}/"

ruby -ryaml -e '
  path = ARGV.fetch(0)
  api_repo = ARGV.fetch(1)
  frontend_repo = ARGV.fetch(2)
  image_tag = ARGV.fetch(3)
  data = YAML.load_file(path)
  data["images"] ||= []
  replacements = {
    "ghcr.io/org/fla-api" => api_repo,
    "ghcr.io/org/fla-frontend" => frontend_repo,
    "localhost:5000/fla-api" => api_repo,
    "localhost:5000/fla-frontend" => frontend_repo,
  }
  data["images"].each do |entry|
    name = entry["name"]
    next unless replacements.key?(name)
    entry["newName"] = replacements[name]
    entry["newTag"] = image_tag
  end
  File.write(path, YAML.dump(data))
' "${TMP_DIR}/kustomization.yaml" "${API_IMAGE_REPO}" "${FRONTEND_IMAGE_REPO}" "${IMAGE_TAG}"

echo "=== Pre-flight checks ==="
kubectl version --client
kubectl cluster-info

echo "=== Rendering overlay ==="
echo "overlay=${OVERLAY}"
echo "namespace=${NAMESPACE}"
echo "api_image=${API_IMAGE}"
echo "frontend_image=${FRONTEND_IMAGE_REPO}:${IMAGE_TAG}"

echo "=== Dry-run validation ==="
render_kustomize "${TMP_DIR}" | kubectl apply --dry-run=client -f - >/dev/null

echo "=== Running migration ==="
"${SCRIPT_DIR}/k8s-migrate.sh" "${IMAGE_TAG}" "${NAMESPACE}" "${API_IMAGE}"

echo "=== Applying manifests ==="
render_kustomize "${TMP_DIR}" | kubectl apply -f -

echo "=== Waiting for rollout ==="
kubectl -n "${NAMESPACE}" rollout status deployment/api --timeout=5m
kubectl -n "${NAMESPACE}" rollout status deployment/worker-default --timeout=5m
kubectl -n "${NAMESPACE}" rollout status deployment/worker-rule --timeout=5m
kubectl -n "${NAMESPACE}" rollout status deployment/worker-llm --timeout=5m
kubectl -n "${NAMESPACE}" rollout status deployment/frontend --timeout=5m

echo "=== Post-apply health check ==="
HEALTHCHECK_POD="tmp-health-check-$(date +%s)"
API_IP="$(kubectl -n "${NAMESPACE}" get svc api -o jsonpath='{.spec.clusterIP}')"
kubectl -n "${NAMESPACE}" run "${HEALTHCHECK_POD}" --image=curlimages/curl --rm -i --restart=Never -- \
  curl -sf "http://${API_IP}:8000/api/v1/health"

echo "=== Deploy complete ==="
