import uuid
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
async def test_analysis_summary(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.analysis.get_analysis_summary", autospec=True) as mock_fn:
            mock_fn.return_value = {
                "total_sessions": 2,
                "total_records": 20,
                "total_errors": 5,
                "accuracy": 0.75,
                "llm_analysed_count": 3,
                "llm_total_cost": 0.123,
            }
            resp = await async_client.get("/api/v1/analysis/summary")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_sessions"] == 2
    assert body["llm_total_cost"] == 0.123


@pytest.mark.asyncio
async def test_error_distribution_invalid_group_by(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        resp = await async_client.get("/api/v1/analysis/error-distribution?group_by=bad")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_error_records_page(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.analysis.get_error_records_page", autospec=True) as mock_fn:
            mock_fn.return_value = {
                "items": [
                    {
                        "id": str(uuid.uuid4()),
                        "session_id": str(uuid.uuid4()),
                        "benchmark": "mmlu",
                        "task_category": "logic",
                        "question_id": "q1",
                        "question": "2+2?",
                        "is_correct": False,
                        "score": 0.0,
                        "error_tags": ["推理性错误.逻辑推理错误"],
                        "has_llm_analysis": True,
                    }
                ],
                "total": 1,
                "page": 1,
                "size": 20,
            }
            resp = await async_client.get("/api/v1/analysis/records?page=1&size=20")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_record_detail_not_found(async_client, _viewer_override):
    from app.main import app

    app.dependency_overrides[get_current_user] = _viewer_override
    try:
        with patch("app.api.v1.routers.analysis.get_record_detail", autospec=True) as mock_fn:
            mock_fn.return_value = None
            resp = await async_client.get(f"/api/v1/analysis/records/{uuid.uuid4()}/detail")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 404
