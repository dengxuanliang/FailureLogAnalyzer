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
async def test_compare_versions(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.compare.compare_versions", autospec=True) as mock_fn:
            mock_fn.return_value = {
                "version_a": "v1",
                "version_b": "v2",
                "benchmark": "mmlu",
                "sessions_a": 1,
                "sessions_b": 1,
                "accuracy_a": 0.7,
                "accuracy_b": 0.8,
                "accuracy_delta": 0.1,
                "error_rate_a": 0.3,
                "error_rate_b": 0.2,
                "error_rate_delta": -0.1,
            }
            resp = await async_client.get("/api/v1/compare/versions?version_a=v1&version_b=v2")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["version_a"] == "v1"
    assert data["version_b"] == "v2"


@pytest.mark.asyncio
async def test_compare_diff(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.compare.get_version_diff", autospec=True) as mock_fn:
            mock_fn.return_value = {
                "version_a": "v1",
                "version_b": "v2",
                "regressed": [],
                "improved": [],
                "new_errors": [],
                "fixed_errors": [],
            }
            resp = await async_client.get("/api/v1/compare/diff?version_a=v1&version_b=v2")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    body = resp.json()
    assert "regressed" in body
    assert "improved" in body


@pytest.mark.asyncio
async def test_compare_radar(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.compare.get_radar_data", autospec=True) as mock_fn:
            mock_fn.return_value = {
                "version_a": "v1",
                "version_b": "v2",
                "dimensions": ["逻辑", "事实"],
                "scores_a": [0.6, 0.8],
                "scores_b": [0.7, 0.85],
            }
            resp = await async_client.get("/api/v1/compare/radar?version_a=v1&version_b=v2")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["dimensions"]) == 2


@pytest.mark.asyncio
async def test_compare_requires_both_versions(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        resp = await async_client.get("/api/v1/compare/versions?version_a=v1")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 422
