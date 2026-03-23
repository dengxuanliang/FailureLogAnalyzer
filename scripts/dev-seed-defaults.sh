#!/usr/bin/env bash
# Seed default rules/strategies/templates into the local database.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PROVIDER="${SEED_LLM_PROVIDER:-openai}"
MODEL="${SEED_LLM_MODEL:-gpt-4o}"
CREATED_BY="${SEED_CREATED_BY:-bootstrap}"

cd "${REPO_ROOT}"

if [[ "${USE_DOCKER:-1}" == "0" ]]; then
  echo "Seeding defaults in local environment..."
  python -m app.cli.seed_defaults --provider "${PROVIDER}" --model "${MODEL}" --created-by "${CREATED_BY}"
  exit 0
fi

command -v docker >/dev/null 2>&1 || {
  echo "Missing required command: docker" >&2
  exit 1
}

echo "Ensuring api service is running..."
docker compose up -d postgres redis api >/dev/null

echo "Seeding defaults in compose environment..."
docker compose exec -T \
  -e SEED_LLM_PROVIDER="${PROVIDER}" \
  -e SEED_LLM_MODEL="${MODEL}" \
  -e SEED_CREATED_BY="${CREATED_BY}" \
  api python -m app.cli.seed_defaults \
    --provider "${PROVIDER}" \
    --model "${MODEL}" \
    --created-by "${CREATED_BY}"

echo "Defaults seeded." 
