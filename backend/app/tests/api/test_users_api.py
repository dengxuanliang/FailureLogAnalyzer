import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.v1.deps import get_current_user
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.db.session import get_db


def _make_user(*, user_id: uuid.UUID | None = None, role: UserRole = UserRole.viewer) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.username = f"user-{role.value}"
    user.email = f"{role.value}@example.com"
    user.password_hash = "hashed"
    user.role = role
    user.is_active = True
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def _override_user(role: UserRole):
    async def _dep():
        return SimpleNamespace(id=uuid.uuid4(), username=role.value, role=role, is_active=True)

    return _dep


def _db_override_factory(db: AsyncMock):
    async def _get_db():
        yield db

    return _get_db


@pytest.mark.asyncio
async def test_list_users_requires_admin(async_client: AsyncClient):
    from app.main import app

    app.dependency_overrides[get_current_user] = _override_user(UserRole.viewer)
    try:
        response = await async_client.get("/api/v1/users")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_returns_serialized_users(async_client: AsyncClient):
    from app.main import app

    users = [_make_user(role=UserRole.admin), _make_user(role=UserRole.analyst)]
    db = AsyncMock()
    db.add = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = users
    db.execute.return_value = result

    app.dependency_overrides[get_current_user] = _override_user(UserRole.admin)
    app.dependency_overrides[get_db] = _db_override_factory(db)
    try:
        response = await async_client.get("/api/v1/users")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    payload = response.json()
    assert [item["username"] for item in payload] == [users[0].username, users[1].username]
    assert payload[0]["role"] == "admin"


@pytest.mark.asyncio
async def test_create_user_hashes_password_and_returns_public_fields(async_client: AsyncClient):
    from app.main import app

    db = AsyncMock()
    db.add = MagicMock()
    db.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=None),
        scalars=MagicMock(),
    )

    async def _refresh(user: User):
        user.id = uuid.uuid4()
        user.created_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)

    db.refresh.side_effect = _refresh

    app.dependency_overrides[get_current_user] = _override_user(UserRole.admin)
    app.dependency_overrides[get_db] = _db_override_factory(db)
    try:
        response = await async_client.post(
            "/api/v1/users",
            json={
                "username": "new-admin",
                "email": "new-admin@example.com",
                "password": "admin12345",
                "role": "admin",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    created_user = db.add.call_args.args[0]
    assert created_user.username == "new-admin"
    assert created_user.password_hash != "admin12345"
    assert response.json()["username"] == "new-admin"
    assert "password_hash" not in response.json()


@pytest.mark.asyncio
async def test_patch_user_updates_password_and_active_flag(async_client: AsyncClient):
    from app.main import app

    user_id = uuid.uuid4()
    existing_user = _make_user(user_id=user_id, role=UserRole.viewer)
    db = AsyncMock()
    db.add = MagicMock()
    db.get.return_value = existing_user
    db.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(return_value=None),
        scalars=MagicMock(),
    )

    app.dependency_overrides[get_current_user] = _override_user(UserRole.admin)
    app.dependency_overrides[get_db] = _db_override_factory(db)
    try:
        response = await async_client.patch(
            f"/api/v1/users/{user_id}",
            json={"password": "next-password", "is_active": False, "role": "analyst"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert existing_user.password_hash != "hashed"
    assert existing_user.is_active is False
    assert existing_user.role == UserRole.analyst
    assert response.json()["role"] == "analyst"
