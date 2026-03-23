from __future__ import annotations

import argparse
import asyncio

from app.db.session import get_async_session
from app.db.models.enums import UserRole
from app.services.user_admin import ensure_user


async def _bootstrap(username: str, email: str, password: str) -> None:
    async with get_async_session() as db:
        created, user = await ensure_user(
            db,
            username=username,
            email=email,
            password=password,
            role=UserRole.admin,
        )
    state = "created" if created else "updated"
    print(f"{state}: {user.username} ({user.email}) role={user.role.value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the first admin user")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="admin12345")
    args = parser.parse_args()
    asyncio.run(_bootstrap(args.username, args.email, args.password))


if __name__ == "__main__":
    main()
