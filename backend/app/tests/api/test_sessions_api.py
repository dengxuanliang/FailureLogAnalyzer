import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.deps import get_current_user
from app.db.models.eval_session import EvalSession
from app.db.models.user import User
from app.db.session import get_db


def _fake_user() -> User:
    user = MagicMock(spec=User)
    user.is_active = True
    return user


def _override_auth():
    async def _dep():
        return _fake_user()

    return _dep


def _make_session(
    *,
    session_id: uuid.UUID | None = None,
    model: str = "gpt",
    model_version: str = "v1",
    benchmark: str = "mmlu",
):
    session = MagicMock(spec=EvalSession)
    session.id = session_id or uuid.uuid4()
    session.model = model
    session.model_version = model_version
    session.benchmark = benchmark
    session.dataset_name = None
    session.total_count = None
    session.error_count = None
    session.accuracy = None
    session.tags = None
    session.created_at = datetime.now(timezone.utc)
    return session


@pytest.mark.asyncio
async def test_list_sessions_returns_frontend_compatible_shape(async_client):
    from app.main import app

    rows = [_make_session(model_version="v2"), _make_session(model_version="v1")]
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = rows
    db.execute = AsyncMock(return_value=execute_result)

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_auth()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.get("/api/v1/sessions")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert set(body[0].keys()) == {
        "id",
        "model",
        "model_version",
        "benchmark",
        "dataset_name",
        "total_count",
        "error_count",
        "accuracy",
        "tags",
        "created_at",
    }
    assert body[0]["total_count"] == 0
    assert body[0]["error_count"] == 0
    assert body[0]["accuracy"] == 0.0
    assert body[0]["tags"] == []


@pytest.mark.asyncio
async def test_get_session_detail_returns_normalized_shape(async_client):
    from app.main import app

    session = _make_session()
    session.updated_at = session.created_at
    db = AsyncMock()
    db.get = AsyncMock(return_value=session)

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_auth()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.get(f"/api/v1/sessions/{session.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(session.id)
    assert body["model_version"] == session.model_version
    assert body["total_count"] == 0
    assert body["error_count"] == 0
    assert body["accuracy"] == 0.0


@pytest.mark.asyncio
async def test_get_session_detail_returns_404_when_missing(async_client):
    from app.main import app

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_auth()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_returns_deleted_payload(async_client):
    from app.main import app

    session = _make_session()
    db = AsyncMock()
    db.get = AsyncMock(return_value=session)
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_auth()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.delete(f"/api/v1/sessions/{session.id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body == {"session_id": str(session.id), "deleted": True}
    db.delete.assert_awaited_once_with(session)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_session_returns_404_when_missing(async_client):
    from app.main import app

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_auth()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.delete(f"/api/v1/sessions/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
    db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_rerun_rules_dispatches_background_job(async_client):
    from app.main import app

    session = _make_session()
    db = AsyncMock()
    db.get = AsyncMock(return_value=session)

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_auth()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        with patch("app.api.v1.routers.sessions.run_rules") as mock_run_rules:
            mock_run_rules.delay.return_value = MagicMock(id="celery-rule-job-1")
            resp = await async_client.post(
                f"/api/v1/sessions/{session.id}/actions/rerun-rules",
                json={"rule_ids": ["rule.a"]},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 202
    body = resp.json()
    assert body["job_id"] == "celery-rule-job-1"
    assert body["session_id"] == str(session.id)
    mock_run_rules.delay.assert_called_once_with(str(session.id), ["rule.a"])
