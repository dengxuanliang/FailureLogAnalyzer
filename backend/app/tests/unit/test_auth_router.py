import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from app.main import app
from app.db.models.enums import UserRole


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
