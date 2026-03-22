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
async def test_benchmark_matrix(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.cross_benchmark.get_benchmark_matrix", autospec=True) as mock_fn:
            mock_fn.return_value = {
                "models": ["v1", "v2"],
                "benchmarks": ["mmlu", "gsm8k"],
                "matrix": [[0.7, 0.6], [0.8, 0.7]],
            }
            resp = await async_client.get("/api/v1/cross-benchmark/matrix")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    body = resp.json()
    assert "models" in body
    assert "benchmarks" in body
    assert "matrix" in body


@pytest.mark.asyncio
async def test_systematic_weaknesses(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.cross_benchmark.get_systematic_weaknesses", autospec=True) as mock_fn:
            mock_fn.return_value = {
                "weaknesses": [
                    {
                        "tag": "推理性错误.逻辑推理错误",
                        "affected_benchmarks": ["mmlu"],
                        "avg_error_rate": 0.35,
                    }
                ]
            }
            resp = await async_client.get("/api/v1/cross-benchmark/weakness")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    assert "weaknesses" in resp.json()
