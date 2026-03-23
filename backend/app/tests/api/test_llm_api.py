"""Tests for /api/v1/llm endpoints using mocked DB/task layers."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps import get_current_user
from app.db.models.user import User
from app.db.models.enums import UserRole, StrategyType
from app.db.models.prompt_template import PromptTemplate
from app.db.models.analysis_strategy import AnalysisStrategy
from app.db.models.eval_session import EvalSession
from app.db.session import get_db


def _make_analyst_user():
    user = MagicMock(spec=User)
    user.is_active = True
    user.role = UserRole.analyst
    user.username = "analyst_user"
    return user


def _make_viewer_user():
    user = MagicMock(spec=User)
    user.is_active = True
    user.role = UserRole.viewer
    user.username = "viewer_user"
    return user


def _analyst_override():
    async def _dep():
        return _make_analyst_user()

    return _dep


def _viewer_override():
    async def _dep():
        return _make_viewer_user()

    return _dep


def _make_template(template_id: uuid.UUID | None = None):
    template = MagicMock(spec=PromptTemplate)
    template.id = template_id or uuid.uuid4()
    template.name = "default-template"
    template.benchmark = "mmlu"
    template.template = "Q:{question}\nA:{model_answer}"
    template.version = 1
    template.is_active = True
    template.created_by = "analyst_user"
    template.created_at = datetime.now(timezone.utc)
    template.updated_at = datetime.now(timezone.utc)
    return template


def _make_strategy(strategy_id: uuid.UUID | None = None, template_id: uuid.UUID | None = None):
    strategy = MagicMock(spec=AnalysisStrategy)
    strategy.id = strategy_id or uuid.uuid4()
    strategy.name = "default-strategy"
    strategy.strategy_type = StrategyType.full
    strategy.config = {"requests_per_minute": 60}
    strategy.llm_provider = "openai"
    strategy.llm_model = "gpt-4o"
    strategy.prompt_template_id = template_id or uuid.uuid4()
    strategy.max_concurrent = 1
    strategy.daily_budget = 10.0
    strategy.is_active = True
    strategy.created_by = "analyst_user"
    strategy.created_at = datetime.now(timezone.utc)
    strategy.updated_at = datetime.now(timezone.utc)
    return strategy


def _make_eval_session(session_id: uuid.UUID):
    session = MagicMock(spec=EvalSession)
    session.id = session_id
    return session


def _make_db(templates=None, strategies=None):
    templates = templates or []
    strategies = strategies or []
    db = AsyncMock()

    async def _execute(stmt):
        result = MagicMock()
        stmt_text = str(stmt)
        if "prompt_templates" in stmt_text:
            result.scalars.return_value.all.return_value = list(templates)
            return result
        if "analysis_strategies" in stmt_text:
            result.scalars.return_value.all.return_value = list(strategies)
            return result
        raise AssertionError(f"Unexpected stmt: {stmt_text}")

    async def _get(model, pk):
        if model is PromptTemplate:
            for item in templates:
                if item.id == pk:
                    return item
            return None
        if model is AnalysisStrategy:
            for item in strategies:
                if item.id == pk:
                    return item
            return None
        if model is EvalSession:
            return _make_eval_session(pk)
        return None

    db.execute = _execute
    db.get = _get
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_list_templates(async_client: AsyncClient):
    from app.main import app

    db = _make_db(templates=[_make_template()])

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.get("/api/v1/llm/templates")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_create_template_requires_analyst_role(async_client: AsyncClient):
    from app.main import app

    db = _make_db()

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _viewer_override()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.post(
            "/api/v1/llm/templates",
            json={
                "name": "t1",
                "benchmark": "mmlu",
                "template": "Q:{question}",
                "version": 1,
                "is_active": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_trigger_llm_job(async_client: AsyncClient):
    from app.main import app

    strategy = _make_strategy()
    db = _make_db(strategies=[strategy])

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db

    with patch("app.api.v1.routers.llm.create_job", new=AsyncMock()) as create_job_mock, patch(
        "app.api.v1.routers.llm.update_job", new=AsyncMock(return_value={})), patch(
        "app.api.v1.routers.llm.run_llm_judge.delay",
        return_value=MagicMock(id="celery-task-id"),
    ):
        try:
            resp = await async_client.post(
                "/api/v1/llm/jobs/trigger",
                json={
                    "session_id": str(uuid.uuid4()),
                    "strategy_id": str(strategy.id),
                    "manual_record_ids": [],
                },
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 202
    data = resp.json()
    assert data["celery_task_id"] == "celery-task-id"
    assert data["status"] == "queued"
    create_job_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_llm_job_status_not_found(async_client: AsyncClient):
    from app.main import app

    db = _make_db()

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    with patch("app.api.v1.routers.llm.get_job_status", new=AsyncMock(return_value=None)):
        try:
            resp = await async_client.get(f"/api/v1/llm/jobs/{uuid.uuid4()}/status")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_llm_jobs(async_client: AsyncClient):
    from app.main import app

    db = _make_db()

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    jobs = [
        {
            "job_id": "job-1",
            "session_id": str(uuid.uuid4()),
            "strategy_id": str(uuid.uuid4()),
            "status": "queued",
            "processed": 0,
            "total": None,
            "succeeded": 0,
            "failed": 0,
            "total_cost": 0.0,
            "stop_reason": None,
            "reason": "",
            "celery_task_id": "celery-1",
            "created_at": 1.0,
            "updated_at": 1.5,
        }
    ]
    with patch("app.api.v1.routers.llm.list_jobs", new=AsyncMock(return_value=jobs)):
        try:
            resp = await async_client.get("/api/v1/llm/jobs")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["job_id"] == "job-1"
    assert data[0]["celery_task_id"] == "celery-1"


@pytest.mark.asyncio
async def test_get_global_llm_cost_summary(async_client: AsyncClient):
    from app.main import app

    db = _make_db()

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    with patch(
        "app.api.v1.routers.llm.get_global_cost_summary",
        new=AsyncMock(
            return_value={
                "total_calls": 12,
                "total_cost": 3.75,
                "sessions_with_llm": 4,
                "by_model": [
                    {"llm_model": "gpt-4o", "calls": 10, "total_cost": 3.5},
                    {"llm_model": "claude-sonnet-4", "calls": 2, "total_cost": 0.25},
                ],
            }
        ),
    ):
        try:
            resp = await async_client.get("/api/v1/llm/cost-summary")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] == 12
    assert data["total_cost"] == 3.75
    assert data["sessions_with_llm"] == 4
    assert data["by_model"][0]["llm_model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_prompt_templates_alias_endpoints(async_client: AsyncClient):
    from app.main import app

    template = _make_template()
    db = _make_db(templates=[template])

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        list_resp = await async_client.get("/api/v1/llm/prompt-templates")
        update_resp = await async_client.put(
            f"/api/v1/llm/prompt-templates/{template.id}",
            json={"is_active": False},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert update_resp.status_code == 200
    assert update_resp.json()["id"] == str(template.id)


@pytest.mark.asyncio
async def test_prompt_templates_alias_list_supports_real_prompt_template_model(async_client: AsyncClient):
    from app.main import app

    template = PromptTemplate(
        id=uuid.uuid4(),
        name="real-template",
        benchmark="mmlu",
        template="Q:{question}",
        version=1,
        is_active=True,
        created_by="analyst_user",
    )
    template.created_at = datetime.now(timezone.utc)
    db = _make_db(templates=[template])

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.get("/api/v1/llm/prompt-templates")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json()[0]["id"] == str(template.id)


@pytest.mark.asyncio
async def test_put_strategy_alias_updates_strategy(async_client: AsyncClient):
    from app.main import app

    strategy = _make_strategy()
    db = _make_db(strategies=[strategy])

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.put(
            f"/api/v1/llm/strategies/{strategy.id}",
            json={"is_active": False},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json()["id"] == str(strategy.id)
