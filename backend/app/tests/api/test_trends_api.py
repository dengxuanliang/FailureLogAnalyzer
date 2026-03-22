from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.deps import get_current_user
from app.db.models.enums import UserRole


@pytest.fixture
def _viewer_override():
    async def _dep():
        user = MagicMock()
        user.role = UserRole.viewer
        user.username = "viewer"
        user.is_active = True
        return user

    return _dep


@pytest.mark.asyncio
async def test_trends(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.trends.get_error_trends", autospec=True) as mock_fn:
            mock_fn.return_value = {
                "data_points": [
                    {"date": "2026-03-18", "error_rate": 0.3, "benchmark": "mmlu", "model_version": "v1"}
                ]
            }
            resp = await async_client.get("/api/v1/trends")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    assert "data_points" in resp.json()


@pytest.mark.asyncio
async def test_trends_with_filters(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.trends.get_error_trends", autospec=True) as mock_fn:
            mock_fn.return_value = {"data_points": []}
            resp = await async_client.get("/api/v1/trends?benchmark=mmlu&model_version=v1")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
