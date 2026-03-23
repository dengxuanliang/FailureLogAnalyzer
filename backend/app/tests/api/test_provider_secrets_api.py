from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.v1.deps import get_current_user
from app.db.models.enums import UserRole
from app.db.session import get_db


def _override_user(role: UserRole):
    async def _dep():
        return SimpleNamespace(id=uuid.uuid4(), username=role.value, role=role, is_active=True)

    return _dep


def _build_secret(*, provider: str = "openai", name: str = "primary") -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(),
        provider=provider,
        name=name,
        encrypted_secret="enc:xxxx",
        secret_mask="sk-12...cdef",
        is_active=True,
        is_default=(name == "primary"),
        created_by="admin",
        created_at=now,
        updated_at=now,
    )


def _db_override_factory(*, records: list[SimpleNamespace]):
    db = AsyncMock()

    async def _execute(stmt):
        stmt_text = str(stmt)
        result = MagicMock()

        if "provider_secrets" in stmt_text and "SELECT" in stmt_text:
            result.scalars.return_value.all.return_value = list(records)
            result.scalars.return_value.first.return_value = records[0] if records else None
            return result

        if "UPDATE provider_secrets" in stmt_text:
            return result

        raise AssertionError(f"Unexpected stmt: {stmt_text}")

    async def _get(_model, pk):
        for row in records:
            if row.id == pk:
                return row
        return None

    async def _refresh(row):
        if not getattr(row, "id", None):
            row.id = uuid.uuid4()
        if not getattr(row, "created_at", None):
            row.created_at = datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)

    db.execute.side_effect = _execute
    db.get.side_effect = _get
    db.refresh.side_effect = _refresh
    db.add = MagicMock(side_effect=lambda row: records.append(row))
    db.delete = AsyncMock(side_effect=lambda row: records.remove(row))
    db.commit = AsyncMock()

    async def _get_db():
        yield db

    return db, _get_db


@pytest.mark.asyncio
async def test_provider_secrets_requires_admin(async_client: AsyncClient):
    from app.main import app

    app.dependency_overrides[get_current_user] = _override_user(UserRole.viewer)
    try:
        response = await async_client.get("/api/v1/llm/provider-secrets")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_provider_secrets_returns_masked_rows(async_client: AsyncClient):
    from app.main import app

    rows = [_build_secret()]
    _, get_db_override = _db_override_factory(records=rows)

    app.dependency_overrides[get_current_user] = _override_user(UserRole.admin)
    app.dependency_overrides[get_db] = get_db_override
    try:
        response = await async_client.get("/api/v1/llm/provider-secrets")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    body = response.json()
    assert body[0]["provider"] == "openai"
    assert body[0]["secret_mask"] == "sk-12...cdef"
    assert "encrypted_secret" not in body[0]


@pytest.mark.asyncio
async def test_create_provider_secret_sets_mask_and_returns_sanitized_payload(async_client: AsyncClient):
    from app.main import app

    rows: list[SimpleNamespace] = []
    db, get_db_override = _db_override_factory(records=rows)

    app.dependency_overrides[get_current_user] = _override_user(UserRole.admin)
    app.dependency_overrides[get_db] = get_db_override
    try:
        response = await async_client.post(
            "/api/v1/llm/provider-secrets",
            json={
                "provider": "openai",
                "name": "primary",
                "secret": "sk-test-123456",
                "is_active": True,
                "is_default": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 201
    payload = response.json()
    assert payload["provider"] == "openai"
    assert payload["secret_mask"].startswith("sk-")
    assert payload["is_default"] is True
    created = db.add.call_args.args[0]
    assert created.encrypted_secret != "sk-test-123456"


@pytest.mark.asyncio
async def test_patch_provider_secret_can_rotate_value_and_promote_default(async_client: AsyncClient):
    from app.main import app

    row = _build_secret(name="backup")
    row.is_default = False
    original_encrypted = row.encrypted_secret
    rows = [row]
    _, get_db_override = _db_override_factory(records=rows)

    app.dependency_overrides[get_current_user] = _override_user(UserRole.admin)
    app.dependency_overrides[get_db] = get_db_override
    try:
        response = await async_client.patch(
            f"/api/v1/llm/provider-secrets/{row.id}",
            json={"secret": "sk-new-abcdef", "is_default": True, "is_active": True},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_default"] is True
    assert row.encrypted_secret != original_encrypted


@pytest.mark.asyncio
async def test_delete_provider_secret(async_client: AsyncClient):
    from app.main import app

    row = _build_secret(name="to-delete")
    rows = [row]
    _, get_db_override = _db_override_factory(records=rows)

    app.dependency_overrides[get_current_user] = _override_user(UserRole.admin)
    app.dependency_overrides[get_db] = get_db_override
    try:
        response = await async_client.delete(f"/api/v1/llm/provider-secrets/{row.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 204
    assert rows == []
