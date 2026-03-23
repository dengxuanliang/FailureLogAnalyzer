import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.deps import get_current_user
from app.db.models.enums import UserRole, ReportStatus, ReportType
from app.db.session import get_db


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)


class _ExecResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _ScalarResult(self._values)


class _FakeDb:
    def __init__(self):
        self._reports = []
        self.add = self._add
        self.commit = AsyncMock()
        self.refresh = AsyncMock(side_effect=self._refresh)
        self.execute = AsyncMock(side_effect=self._execute)
        self.get = AsyncMock(side_effect=self._get)

    def _add(self, report):
        self._reports.append(report)

    async def _refresh(self, report):
        if getattr(report, "id", None) is None:
            report.id = uuid.uuid4()

    async def _execute(self, _stmt):
        return _ExecResult(list(reversed(self._reports))[:100])

    async def _get(self, _model, report_id):
        for report in self._reports:
            if str(report.id) == str(report_id):
                return report
        return None


@pytest.fixture
def fake_db():
    return _FakeDb()


@pytest.fixture
def analyst_user():
    user = SimpleNamespace(role=UserRole.analyst, username="analyst", is_active=True)
    return user


@pytest.fixture
def viewer_user():
    user = SimpleNamespace(role=UserRole.viewer, username="viewer", is_active=True)
    return user


def _override_user(user):
    async def _dep():
        return user

    return _dep


@pytest.mark.asyncio
async def test_generate_report(async_client, fake_db, analyst_user):
    from app.main import app

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = _override_user(analyst_user)
    try:
        with patch("app.api.v1.routers.reports.generate_report", autospec=True) as mock_task:
            mock_task.apply_async.return_value = MagicMock(id="celery-report-uuid-123")

            resp = await async_client.post(
                "/api/v1/reports/generate",
                json={"title": "Test Report", "report_type": "summary"},
            )
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 202
    data = resp.json()
    assert "report_id" in data
    assert data["status"] == ReportStatus.pending.value


@pytest.mark.asyncio
async def test_list_reports(async_client, fake_db, analyst_user):
    from app.main import app

    # Seed one report-like object
    report = SimpleNamespace(
        id=uuid.uuid4(),
        title="Seed",
        report_type=ReportType.summary,
        status=ReportStatus.done,
        benchmark=None,
        model_version=None,
        session_ids=None,
        time_range_start=None,
        time_range_end=None,
        created_by="analyst",
        created_at="2026-03-20T00:00:00Z",
        updated_at="2026-03-20T00:00:00Z",
    )
    fake_db._reports = [report]

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = _override_user(analyst_user)
    try:
        resp = await async_client.get("/api/v1/reports")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["title"] == "Seed"


@pytest.mark.asyncio
async def test_get_report_not_found(async_client, fake_db, analyst_user):
    from app.main import app

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = _override_user(analyst_user)
    try:
        resp = await async_client.get(f"/api/v1/reports/{uuid.uuid4()}")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_report_as_markdown(async_client, fake_db, analyst_user):
    from app.main import app

    report = SimpleNamespace(
        id=uuid.uuid4(),
        title="Seed",
        report_type=ReportType.summary,
        status=ReportStatus.done,
        benchmark="mmlu",
        model_version="v1",
        session_ids=None,
        time_range_start=None,
        time_range_end=None,
        content={"summary": {"total_records": 10, "total_errors": 3}},
        error_message=None,
        created_by="analyst",
        created_at="2026-03-20T00:00:00Z",
        updated_at="2026-03-20T00:00:00Z",
    )
    fake_db._reports = [report]

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = _override_user(analyst_user)
    try:
        resp = await async_client.get(f"/api/v1/reports/{report.id}/export?format=markdown")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    assert "# Seed" in resp.text
    assert "total_records" in resp.text


@pytest.mark.asyncio
async def test_export_report_as_json(async_client, fake_db, analyst_user):
    from app.main import app

    report = SimpleNamespace(
        id=uuid.uuid4(),
        title="Seed",
        report_type=ReportType.summary,
        status=ReportStatus.done,
        benchmark="mmlu",
        model_version="v1",
        session_ids=None,
        time_range_start=None,
        time_range_end=None,
        content={"summary": {"total_records": 10}},
        error_message=None,
        created_by="analyst",
        created_at="2026-03-20T00:00:00Z",
        updated_at="2026-03-20T00:00:00Z",
    )
    fake_db._reports = [report]

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = _override_user(analyst_user)
    try:
        resp = await async_client.get(f"/api/v1/reports/{report.id}/export?format=json")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Seed"
    assert data["content"]["summary"]["total_records"] == 10


@pytest.mark.asyncio
async def test_generate_requires_analyst(async_client, fake_db, viewer_user):
    from app.main import app

    app.dependency_overrides[get_db] = lambda: fake_db
    app.dependency_overrides[get_current_user] = _override_user(viewer_user)
    try:
        resp = await async_client.post(
            "/api/v1/reports/generate",
            json={"title": "Test", "report_type": "summary"},
        )
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 403
