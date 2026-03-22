import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock, call

@pytest.mark.asyncio
async def test_health_returns_200_when_all_ok():
    from app.main import app
    with patch("app.api.v1.routers.health.check_db", new_callable=AsyncMock, return_value=True), \
         patch("app.api.v1.routers.health.check_redis", new_callable=AsyncMock, return_value=True), \
         patch("app.api.v1.routers.health.check_celery", new_callable=AsyncMock, return_value={"ok": True, "workers_online": 1, "workers_per_queue": {"celery": 1}, "queue_depth": {"celery": 0}}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["checks"]["db"] is True
        assert body["checks"]["celery"] is True

@pytest.mark.asyncio
async def test_health_returns_503_when_db_down():
    from app.main import app
    with patch("app.api.v1.routers.health.check_db", new_callable=AsyncMock, return_value=False), \
         patch("app.api.v1.routers.health.check_redis", new_callable=AsyncMock, return_value=True), \
         patch("app.api.v1.routers.health.check_celery", new_callable=AsyncMock, return_value={"ok": True, "workers_online": 1, "workers_per_queue": {"celery": 1}, "queue_depth": {"celery": 0}}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
        assert resp.status_code == 503


@pytest.mark.asyncio
async def test_health_returns_503_when_celery_workers_offline():
    from app.main import app
    with patch("app.api.v1.routers.health.check_db", new_callable=AsyncMock, return_value=True), \
         patch("app.api.v1.routers.health.check_redis", new_callable=AsyncMock, return_value=True), \
         patch("app.api.v1.routers.health.check_celery", new_callable=AsyncMock, return_value={"ok": False, "workers_online": 0, "workers_per_queue": {"celery": 0}, "queue_depth": {"celery": 10}}):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["checks"]["celery"] is False
    assert body["celery"]["workers_online"] == 0


@pytest.mark.asyncio
async def test_check_celery_collects_worker_and_queue_metrics():
    from app.api.v1.routers import health

    fake_redis = AsyncMock()
    fake_redis.llen.side_effect = [5, 2]

    fake_inspect = MagicMock()
    fake_inspect.ping.return_value = {"worker-a@node": {"ok": "pong"}}
    fake_inspect.active_queues.return_value = {
        "worker-a@node": [{"name": "celery"}, {"name": "rule"}]
    }

    with patch("app.api.v1.routers.health.aioredis.from_url", return_value=fake_redis), \
         patch.object(health.celery_app.control, "inspect", return_value=fake_inspect), \
         patch("app.api.v1.routers.health.CELERY_QUEUE_DEPTH") as mock_queue_depth, \
         patch("app.api.v1.routers.health.update_worker_online_metrics", return_value={"celery": 1, "rule": 1}) as mock_worker_update:
        result = await health.check_celery(queue_names={"celery", "rule"})

    assert result["ok"] is True
    assert result["workers_online"] == 1
    assert result["workers_per_queue"] == {"celery": 1, "rule": 1}
    assert result["queue_depth"] == {"celery": 5, "rule": 2}
    assert mock_queue_depth.labels.call_args_list == [call(queue="celery"), call(queue="rule")]
    mock_worker_update.assert_called_once()
