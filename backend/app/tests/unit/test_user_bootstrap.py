from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.auth import verify_password
from app.db.models.enums import UserRole


@pytest.mark.asyncio
async def test_ensure_user_creates_missing_account():
    from app.services.user_admin import ensure_user

    db = AsyncMock()
    db.add = MagicMock()
    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    created, user = await ensure_user(
        db,
        username="admin",
        email="admin@example.com",
        password="admin12345",
        role=UserRole.admin,
    )

    assert created is True
    assert user.username == "admin"
    assert verify_password("admin12345", user.password_hash)
    db.add.assert_called_once_with(user)
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_ensure_user_updates_existing_account():
    from app.services.user_admin import ensure_user

    existing = SimpleNamespace(
        username="admin",
        email="old@example.com",
        password_hash="old-hash",
        role=UserRole.viewer,
        is_active=False,
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=existing))

    created, user = await ensure_user(
        db,
        username="admin",
        email="new@example.com",
        password="new-password",
        role=UserRole.admin,
    )

    assert created is False
    assert user is existing
    assert user.email == "new@example.com"
    assert user.role == UserRole.admin
    assert user.is_active is True
    assert verify_password("new-password", user.password_hash)
    db.add.assert_not_called()
    db.commit.assert_awaited()
