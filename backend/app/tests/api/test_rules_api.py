"""Tests for /api/v1/rules CRUD endpoints using mocked DB."""
import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from httpx import AsyncClient

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.db.models.user import User
from app.db.models.enums import UserRole
from app.db.models.analysis_rule import AnalysisRule


RULE_PAYLOAD = {
    "name": "test_syntax_error",
    "description": "Detects syntax errors",
    "field": "model_answer",
    "condition": {"type": "regex", "pattern": "SyntaxError"},
    "tags": ["格式与规范错误.输出格式不符"],
    "confidence": 0.9,
    "priority": 10,
    "is_active": True,
}


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


def _make_db_rule(name="test_syntax_error", rule_id=None):
    """Build a mock AnalysisRule ORM object."""
    rule = MagicMock(spec=AnalysisRule)
    rule.id = rule_id or uuid.uuid4()
    rule.name = name
    rule.description = "Detects syntax errors"
    rule.field = "model_answer"
    rule.condition = {"type": "regex", "pattern": "SyntaxError"}
    rule.tags = ["格式与规范错误.输出格式不符"]
    rule.confidence = 0.9
    rule.priority = 10
    rule.is_active = True
    rule.created_by = "analyst_user"
    rule.created_at = datetime.now(timezone.utc)
    rule.updated_at = datetime.now(timezone.utc)
    return rule


def _make_db_session(rules_store=None):
    """Create an async mock DB session."""
    if rules_store is None:
        rules_store = []

    db = AsyncMock()

    async def _execute(stmt):
        result = MagicMock()
        result.scalars.return_value.all.return_value = list(rules_store)
        return result

    db.execute = _execute

    async def _get(model, pk):
        for rule in rules_store:
            if rule.id == pk:
                return rule
        return None

    db.get = _get
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.delete = AsyncMock()

    async def _refresh(obj):
        pass

    db.refresh = _refresh
    return db


def _get_test_db_factory(rules_store):
    """Return a get_db override that uses the given rules_store."""
    async def _get_test_db():
        yield _make_db_session(rules_store)
    return _get_test_db


@pytest.mark.asyncio
async def test_list_rules(async_client: AsyncClient):
    from app.main import app
    rules_store = [_make_db_rule()]
    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db_factory(rules_store)
    try:
        resp = await async_client.get("/api/v1/rules")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_get_rule_by_id(async_client: AsyncClient):
    from app.main import app
    rule_id = uuid.uuid4()
    rules_store = [_make_db_rule(rule_id=rule_id)]
    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db_factory(rules_store)
    try:
        resp = await async_client.get(f"/api/v1/rules/{rule_id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(rule_id)


@pytest.mark.asyncio
async def test_get_nonexistent_rule_returns_404(async_client: AsyncClient):
    from app.main import app
    rules_store = []
    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db_factory(rules_store)
    try:
        resp = await async_client.get("/api/v1/rules/00000000-0000-0000-0000-000000000000")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_rule(async_client: AsyncClient):
    from app.main import app
    rules_store = []
    new_rule = _make_db_rule()

    db = _make_db_session(rules_store)

    # After add+commit+refresh, the "rule" should be returned
    async def _refresh(obj):
        # Copy fields from new_rule to simulate DB-generated fields
        obj.id = new_rule.id
        obj.created_at = new_rule.created_at
        obj.updated_at = new_rule.updated_at

    db.refresh = _refresh

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.post("/api/v1/rules", json=RULE_PAYLOAD)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "test_syntax_error"
    assert "id" in data


@pytest.mark.asyncio
async def test_put_rule_full_update(async_client: AsyncClient):
    from app.main import app
    rule_id = uuid.uuid4()
    rule = _make_db_rule(rule_id=rule_id)
    rules_store = [rule]

    db = _make_db_session(rules_store)

    async def _refresh(obj):
        obj.priority = 20

    db.refresh = _refresh

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        updated = {**RULE_PAYLOAD, "priority": 20}
        resp = await async_client.put(f"/api/v1/rules/{rule_id}", json=updated)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200
    assert resp.json()["priority"] == 20


@pytest.mark.asyncio
async def test_patch_rule_partial_update(async_client: AsyncClient):
    from app.main import app
    rule_id = uuid.uuid4()
    rule = _make_db_rule(rule_id=rule_id)
    rules_store = [rule]

    db = _make_db_session(rules_store)

    async def _refresh(obj):
        obj.is_active = False

    db.refresh = _refresh

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        resp = await async_client.patch(f"/api/v1/rules/{rule_id}", json={"is_active": False})
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_rule(async_client: AsyncClient):
    from app.main import app
    rule_id = uuid.uuid4()
    rule = _make_db_rule(rule_id=rule_id)
    rules_store = [rule]

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db_factory(rules_store)
    try:
        resp = await async_client.delete(f"/api/v1/rules/{rule_id}")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_create_rule_requires_analyst_role(async_client: AsyncClient):
    from app.main import app
    app.dependency_overrides[get_current_user] = _viewer_override()
    app.dependency_overrides[get_db] = _get_test_db_factory([])
    try:
        resp = await async_client.post("/api/v1/rules", json=RULE_PAYLOAD)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_rule_duplicate_name_returns_409(async_client: AsyncClient):
    from app.main import app
    from sqlalchemy.exc import IntegrityError

    db = _make_db_session([])

    call_count = [0]

    async def _commit():
        call_count[0] += 1
        if call_count[0] > 1:
            # Simulate duplicate key on second commit
            raise IntegrityError("UNIQUE constraint failed", params={}, orig=Exception("dup"))

    db.commit = _commit

    async def _get_test_db():
        yield db

    app.dependency_overrides[get_current_user] = _analyst_override()
    app.dependency_overrides[get_db] = _get_test_db
    try:
        # First create
        new_rule = _make_db_rule()

        async def _refresh(obj):
            obj.id = new_rule.id
            obj.created_at = new_rule.created_at
            obj.updated_at = new_rule.updated_at

        db.refresh = _refresh
        await async_client.post("/api/v1/rules", json=RULE_PAYLOAD)

        # Second create (same name) — db will raise IntegrityError
        resp = await async_client.post("/api/v1/rules", json=RULE_PAYLOAD)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 409
