from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.deps import get_current_user
from app.api.v1.routers.analysis import router as analysis_router
from app.api.v1.routers.llm import router as llm_router
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.db.session import get_db


@pytest.fixture
def analyst_user() -> User:
    user = MagicMock(spec=User)
    user.is_active = True
    user.role = UserRole.analyst
    user.username = "demo_analyst"
    return user


@pytest.fixture
def viewer_user() -> User:
    user = MagicMock(spec=User)
    user.is_active = True
    user.role = UserRole.viewer
    user.username = "demo_viewer"
    return user


@pytest.fixture
async def compat_client() -> AsyncClient:
    app = FastAPI()
    app.include_router(analysis_router, prefix="/api/v1")
    app.include_router(llm_router, prefix="/api/v1")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.app = app  # type: ignore[attr-defined]
        yield client


@pytest.mark.asyncio
async def test_manual_tag_update_endpoint_exists_and_returns_saved_tags(compat_client: AsyncClient, analyst_user: User):
    db = AsyncMock()

    async def _db_dep():
        yield db

    async def _user_dep():
        return analyst_user

    compat_client.app.dependency_overrides[get_db] = _db_dep  # type: ignore[attr-defined]
    compat_client.app.dependency_overrides[get_current_user] = _user_dep  # type: ignore[attr-defined]

    record_id = uuid.uuid4()
    payload = {"record_id": str(record_id), "saved_tags": ["推理性错误.逻辑推理.推理链断裂"]}

    with patch(
        "app.api.v1.routers.analysis.update_record_error_tags",
        new=AsyncMock(return_value=payload),
    ) as update_mock:
        try:
            response = await compat_client.patch(
                f"/api/v1/analysis/records/{record_id}/tags",
                json={"tags": payload["saved_tags"], "note": "demo"},
            )
        finally:
            compat_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert response.json() == payload
    update_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_manual_tag_update_endpoint_requires_analyst_role(compat_client: AsyncClient, viewer_user: User):
    db = AsyncMock()

    async def _db_dep():
        yield db

    async def _user_dep():
        return viewer_user

    compat_client.app.dependency_overrides[get_db] = _db_dep  # type: ignore[attr-defined]
    compat_client.app.dependency_overrides[get_current_user] = _user_dep  # type: ignore[attr-defined]

    try:
        response = await compat_client.patch(
            f"/api/v1/analysis/records/{uuid.uuid4()}/tags",
            json={"tags": ["格式性错误.输出格式不符"]},
        )
    finally:
        compat_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_llm_trigger_alias_endpoint_exists(compat_client: AsyncClient, analyst_user: User):
    db = AsyncMock()

    async def _db_dep():
        yield db

    async def _user_dep():
        return analyst_user

    compat_client.app.dependency_overrides[get_db] = _db_dep  # type: ignore[attr-defined]
    compat_client.app.dependency_overrides[get_current_user] = _user_dep  # type: ignore[attr-defined]

    record_id = uuid.uuid4()
    expected = {"job_id": "job-123", "celery_task_id": "celery-123", "status": "queued"}

    with patch(
        "app.api.v1.routers.llm.trigger_llm_job_compat_by_record_ids",
        new=AsyncMock(return_value=expected),
    ) as compat_mock:
        try:
            response = await compat_client.post(
                "/api/v1/llm/trigger",
                json={"record_ids": [str(record_id)], "strategy": "manual"},
            )
        finally:
            compat_client.app.dependency_overrides.clear()  # type: ignore[attr-defined]

    assert response.status_code == 202
    assert response.json() == expected
    compat_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_llm_trigger_alias_falls_back_to_any_active_strategy_when_manual_missing() -> None:
    from app.api.v1.routers.llm import LlmTriggerCompatRequest, trigger_llm_job_compat_by_record_ids
    from app.db.models.enums import StrategyType

    record_id = uuid.uuid4()
    session_id = uuid.uuid4()
    fallback_strategy_id = uuid.uuid4()

    record = MagicMock()
    record.id = record_id
    record.session_id = session_id

    fallback_strategy = MagicMock()
    fallback_strategy.id = fallback_strategy_id
    fallback_strategy.strategy_type = StrategyType.fallback

    record_result = MagicMock()
    record_result.scalars.return_value.all.return_value = [record]

    no_manual_strategy_result = MagicMock()
    no_manual_strategy_result.scalars.return_value.first.return_value = None

    fallback_strategy_result = MagicMock()
    fallback_strategy_result.scalars.return_value.first.return_value = fallback_strategy

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            record_result,
            no_manual_strategy_result,
            fallback_strategy_result,
        ]
    )

    with patch(
        "app.api.v1.routers.llm._enqueue_llm_job",
        new=AsyncMock(return_value={"job_id": "job-1", "celery_task_id": "celery-1", "status": "queued"}),
    ) as enqueue_mock:
        result = await trigger_llm_job_compat_by_record_ids(
            payload=LlmTriggerCompatRequest(record_ids=[record_id], strategy="manual"),
            db=db,
        )

    assert result["status"] == "queued"
    enqueue_mock.assert_awaited_once_with(
        session_id=session_id,
        strategy_id=fallback_strategy_id,
        manual_record_ids=[record_id],
    )
