#!/usr/bin/env bash
set -euo pipefail

MACHINE_NAME="${1:-pmapple}"
MIRROR_HOST="${MIRROR_HOST:-docker.m.daocloud.io}"
PODMAN_API_SOCK="${PODMAN_API_SOCK:-unix:///var/folders/g9/xmxk53c11fj53d9_5smnygs80000gn/T/podman/${MACHINE_NAME}-api.sock}"

command -v podman >/dev/null 2>&1 || {
  echo "podman is required" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || {
  echo "docker CLI is required" >&2
  exit 1
}

echo "== ensure podman machine is running =="
if ! podman machine list | grep -q "^${MACHINE_NAME}[[:space:]].*Currently running"; then
  podman machine start "${MACHINE_NAME}"
fi

echo "== configure docker.io rewrite to ${MIRROR_HOST} inside ${MACHINE_NAME} =="
podman machine ssh "${MACHINE_NAME}" "sudo tee /etc/containers/registries.conf.d/100-dockerhub-mirror.conf >/dev/null <<'EOF'
[[registry]]
prefix = \"docker.io\"
location = \"${MIRROR_HOST}\"
EOF"

echo "== restart machine so the remote API picks up registry config =="
podman machine stop "${MACHINE_NAME}"
podman machine start "${MACHINE_NAME}"

echo "== verify podman remote pull from docker.io succeeds =="
podman --url "${PODMAN_API_SOCK}" pull docker.io/library/hello-world

echo "== verify docker CLI can pull through podman backend =="
docker run --rm busybox echo docker-ok

echo
echo "Mirror configured successfully for ${MACHINE_NAME}."
echo "docker.io -> ${MIRROR_HOST}"
