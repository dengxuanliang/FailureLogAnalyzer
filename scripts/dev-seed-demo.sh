#!/usr/bin/env bash
# Seed demo sessions/records inside the Compose API container.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FORCE="${DEMO_SEED_FORCE:-0}"

command -v docker >/dev/null 2>&1 || {
  echo "Missing required command: docker" >&2
  exit 1
}

cd "${REPO_ROOT}"

echo "Ensuring api service is running..."
docker compose up -d postgres redis api >/dev/null

COMMAND=(docker compose exec -T api python -m app.cli.seed_demo)
if [[ "${FORCE}" == "1" || "${FORCE}" == "true" ]]; then
  COMMAND+=(--force)
fi

echo "Seeding demo data..."
"${COMMAND[@]}"

echo "Demo seed complete."
