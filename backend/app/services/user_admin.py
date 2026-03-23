from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.db.models.enums import UserRole
from app.db.models.user import User


async def find_user_by_username_or_email(
    db: AsyncSession,
    *,
    username: str | None = None,
    email: str | None = None,
) -> User | None:
    clauses = []
    if username:
        clauses.append(User.username == username)
    if email:
        clauses.append(User.email == email)
    if not clauses:
        return None
    result = await db.execute(select(User).where(or_(*clauses)))
    return result.scalar_one_or_none()


async def ensure_user(
    db: AsyncSession,
    *,
    username: str,
    email: str,
    password: str,
    role: UserRole,
) -> tuple[bool, User]:
    existing = await find_user_by_username_or_email(db, username=username)
    created = existing is None
    user = existing or User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    if existing is None:
        db.add(user)
    else:
        user.email = email
        user.password_hash = hash_password(password)
        user.role = role
        user.is_active = True

    await db.commit()
    await db.refresh(user)
    return created, user
