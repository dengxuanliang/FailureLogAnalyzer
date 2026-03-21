import pytest
import io
from unittest.mock import patch, MagicMock, AsyncMock

from app.api.v1.deps import get_current_user
from app.db.models.user import User


def _fake_user():
    """Return a minimal mock User for auth bypass."""
    user = MagicMock(spec=User)
    user.is_active = True
    return user


def _override_auth():
    """FastAPI dependency override that skips real auth."""
    async def _dep():
        return _fake_user()
    return _dep


@pytest.fixture
def _reset_watcher():
    import app.api.v1.ingest as ingest_api

    ingest_api._active_watcher = None
    yield
    ingest_api._active_watcher = None


@pytest.mark.asyncio
async def test_upload_returns_job_id(async_client):
    from app.main import app
    app.dependency_overrides[get_current_user] = _override_auth()
    try:
        content = b'{"question_id":"q1","question":"x","expected_answer":"a","model_answer":"b","is_correct":false}\n'

        with patch("app.api.v1.ingest.parse_file") as mock_task, \
             patch("app.api.v1.ingest.save_upload_file", new=AsyncMock(return_value="/tmp/upload/test.jsonl")), \
             patch("app.api.v1.ingest.create_job", new=AsyncMock(return_value=None)), \
             patch("app.api.v1.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())):
            mock_task.delay.return_value = MagicMock(id="celery-task-1")

            resp = await async_client.post(
                "/api/v1/ingest/upload",
                files={"file": ("test.jsonl", io.BytesIO(content), "application/octet-stream")},
                data={
                    "benchmark": "generic",
                    "model": "test-model",
                    "model_version": "v1",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert "session_id" in body


@pytest.mark.asyncio
async def test_upload_rejects_non_json_file(async_client):
    from app.main import app
    app.dependency_overrides[get_current_user] = _override_auth()
    try:
        content = b"this is not json at all"
        resp = await async_client.post(
            "/api/v1/ingest/upload",
            files={"file": ("data.csv", io.BytesIO(content), "text/csv")},
            data={"benchmark": "generic", "model": "m", "model_version": "v"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_job_status_returns_progress(async_client):
    from app.main import app
    app.dependency_overrides[get_current_user] = _override_auth()
    try:
        with patch("app.api.v1.ingest.get_job_status", new=AsyncMock(return_value={
            "job_id": "job-123",
            "status": "running",
            "processed": 500,
            "total": 1000,
        })), \
        patch("app.api.v1.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())):
            resp = await async_client.get("/api/v1/ingest/job-123/status")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "running"


@pytest.mark.asyncio
async def test_job_status_404_for_unknown_job(async_client):
    from app.main import app
    app.dependency_overrides[get_current_user] = _override_auth()
    try:
        with patch("app.api.v1.ingest.get_job_status", new=AsyncMock(return_value=None)), \
             patch("app.api.v1.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())):
            resp = await async_client.get("/api/v1/ingest/unknown-job/status")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_directory_ingest_queues_multiple_jobs(async_client, tmp_path):
    from app.main import app
    app.dependency_overrides[get_current_user] = _override_auth()
    try:
        # Create two jsonl files
        for i in range(2):
            f = tmp_path / f"file{i}.jsonl"
            f.write_text('{"question_id":"q1","question":"x","expected_answer":"a","model_answer":"b","is_correct":false}\n')

        with patch("app.api.v1.ingest.parse_file") as mock_task, \
             patch("app.api.v1.ingest.create_job", new=AsyncMock(return_value=None)), \
             patch("app.api.v1.ingest.get_redis", new=AsyncMock(return_value=AsyncMock())), \
             patch("app.api.v1.ingest.settings") as mock_settings:
            mock_settings.UPLOAD_DIR = str(tmp_path)
            mock_task.delay.return_value = MagicMock(id="celery-task-x")

            resp = await async_client.post(
                "/api/v1/ingest/directory",
                json={
                    "directory_path": str(tmp_path),
                    "benchmark": "generic",
                    "model": "test-model",
                    "model_version": "v1",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 202
    body = resp.json()
    assert len(body["jobs"]) == 2


@pytest.mark.asyncio
async def test_watcher_start_returns_running(async_client, tmp_path, _reset_watcher):
    from app.main import app

    app.dependency_overrides[get_current_user] = _override_auth()
    try:
        with patch("app.api.v1.ingest.DirectoryWatcher") as mock_watcher_cls:
            watcher = MagicMock()
            watcher.is_running = True
            mock_watcher_cls.return_value = watcher

            resp = await async_client.post(
                "/api/v1/ingest/watcher/start",
                json={"watch_dir": str(tmp_path)},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    assert resp.json() == {"running": True, "watch_dir": str(tmp_path)}


@pytest.mark.asyncio
async def test_watcher_stop_returns_not_running(async_client, _reset_watcher):
    from app.main import app
    import app.api.v1.ingest as ingest_api

    app.dependency_overrides[get_current_user] = _override_auth()
    try:
        watcher = MagicMock()
        watcher.is_running = True
        ingest_api._active_watcher = watcher

        resp = await async_client.post("/api/v1/ingest/watcher/stop")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    assert resp.json() == {"running": False, "watch_dir": None}
    watcher.stop.assert_called_once()


@pytest.mark.asyncio
async def test_watcher_status_reflects_running_watcher(async_client, tmp_path, _reset_watcher):
    from app.main import app
    import app.api.v1.ingest as ingest_api

    app.dependency_overrides[get_current_user] = _override_auth()
    try:
        watcher = MagicMock()
        watcher.is_running = True
        watcher.watch_dir = tmp_path
        ingest_api._active_watcher = watcher

        resp = await async_client.get("/api/v1/ingest/watcher/status")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200
    assert resp.json() == {"running": True, "watch_dir": str(tmp_path)}
