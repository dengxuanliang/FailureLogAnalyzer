#!/usr/bin/env bash
# Run Alembic upgrade head as a Kubernetes Job.
# Usage: ./scripts/k8s-migrate.sh [image_tag] [namespace]
set -euo pipefail

IMAGE_TAG="${1:-latest}"
NAMESPACE="${2:-fla}"
JOB_NAME="alembic-migrate-$(date +%s)"

kubectl -n "${NAMESPACE}" apply -f - <<EOF_INNER
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
  namespace: ${NAMESPACE}
spec:
  ttlSecondsAfterFinished: 3600
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: ghcr.io/org/fla-api:${IMAGE_TAG}
          command: ["alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: fla-api-config
            - secretRef:
                name: fla-api
EOF_INNER

echo "Waiting for migration job ${JOB_NAME} in namespace ${NAMESPACE}..."
kubectl -n "${NAMESPACE}" wait job/"${JOB_NAME}" \
  --for=condition=complete \
  --timeout=300s

echo "Migration logs:"
kubectl -n "${NAMESPACE}" logs job/"${JOB_NAME}"
echo "Migration complete."
