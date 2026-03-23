import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app
from app.db.models.enums import UserRole
from app.db.session import get_db
from app.core.auth import decode_access_token, verify_password


class _NoopTransaction:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _db_override_factory(db):
    async def _get_db():
        yield db

    return _get_db


def _mock_bootstrap_db(*, existing_user_id: uuid.UUID | None):
    db = AsyncMock()
    db.add = MagicMock()
    db.begin = MagicMock(return_value=_NoopTransaction())

    existing_user_result = MagicMock()
    existing_user_result.scalar_one_or_none.return_value = existing_user_id
    db.execute.side_effect = [MagicMock(), existing_user_result]

    async def _refresh(user):
        now = datetime.now(timezone.utc)
        user.id = uuid.uuid4()
        user.created_at = now
        user.updated_at = now

    db.refresh.side_effect = _refresh
    return db


@pytest.mark.asyncio
async def test_login_returns_token_shape():
    mock_user = MagicMock()
    mock_user.id = "00000000-0000-0000-0000-000000000001"
    mock_user.role = UserRole.analyst
    mock_user.is_active = True

    with patch("app.api.v1.routers.auth.authenticate_user", return_value=mock_user):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": "test", "password": "pass"}
            )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_returns_401_on_bad_credentials():
    with patch("app.api.v1.routers.auth.authenticate_user", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": "bad", "password": "wrong"}
            )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bootstrap_returns_201_with_jwt_and_admin_user_when_no_users_exist():
    db = _mock_bootstrap_db(existing_user_id=None)
    app.dependency_overrides[get_db] = _db_override_factory(db)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/bootstrap",
                json={
                    "username": "bootstrap-admin",
                    "email": "bootstrap-admin@example.com",
                    "password": "admin12345",
                },
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["username"] == "bootstrap-admin"
    assert body["user"]["email"] == "bootstrap-admin@example.com"
    assert body["user"]["role"] == "admin"
    assert body["user"]["is_active"] is True

    token_payload = decode_access_token(body["access_token"])
    assert token_payload["sub"] == body["user"]["id"]
    assert token_payload["role"] == "admin"

    created_user = db.add.call_args.args[0]
    assert created_user.role == UserRole.admin
    assert verify_password("admin12345", created_user.password_hash)


@pytest.mark.asyncio
async def test_bootstrap_returns_409_when_users_table_is_not_empty():
    db = _mock_bootstrap_db(existing_user_id=uuid.uuid4())
    app.dependency_overrides[get_db] = _db_override_factory(db)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/bootstrap",
                json={
                    "username": "bootstrap-admin",
                    "email": "bootstrap-admin@example.com",
                    "password": "admin12345",
                },
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Bootstrap already completed"
    db.add.assert_not_called()
    db.refresh.assert_not_awaited()
