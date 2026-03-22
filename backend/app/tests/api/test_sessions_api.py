import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

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
