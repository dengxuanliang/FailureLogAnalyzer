#!/usr/bin/env bash
# Create or update a local demo admin user inside the Compose API container.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

USERNAME="${DEMO_USERNAME:-admin}"
EMAIL="${DEMO_EMAIL:-admin@example.com}"
PASSWORD="${DEMO_PASSWORD:-admin123456}"

command -v docker >/dev/null 2>&1 || {
  echo "Missing required command: docker" >&2
  exit 1
}

cd "${REPO_ROOT}"

echo "Ensuring api service is running..."
docker compose up -d postgres redis api >/dev/null

echo "Creating/updating demo admin user '${USERNAME}'..."
docker compose exec -T \
  -e DEMO_USERNAME="${USERNAME}" \
  -e DEMO_EMAIL="${EMAIL}" \
  -e DEMO_PASSWORD="${PASSWORD}" \
  api python - <<'PY'
import asyncio
import os

from sqlalchemy import select

from app.core.auth import hash_password
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.db.session import get_async_session

username = os.environ["DEMO_USERNAME"]
email = os.environ["DEMO_EMAIL"]
password = os.environ["DEMO_PASSWORD"]

async def main() -> None:
    async with get_async_session() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.admin,
                is_active=True,
            )
            session.add(user)
        else:
            user.email = email
            user.password_hash = hash_password(password)
            user.role = UserRole.admin
            user.is_active = True

        await session.commit()

asyncio.run(main())
PY

echo "Demo admin ready."
echo "username=${USERNAME}"
echo "email=${EMAIL}"
echo "password=${PASSWORD}"
