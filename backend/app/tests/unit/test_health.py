import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_health_returns_200_when_all_ok():
    from app.main import app
    with patch("app.api.v1.routers.health.check_db", new_callable=AsyncMock, return_value=True), \
         patch("app.api.v1.routers.health.check_redis", new_callable=AsyncMock, return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["checks"]["db"] is True

@pytest.mark.asyncio
async def test_health_returns_503_when_db_down():
    from app.main import app
    with patch("app.api.v1.routers.health.check_db", new_callable=AsyncMock, return_value=False), \
         patch("app.api.v1.routers.health.check_redis", new_callable=AsyncMock, return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/health")
        assert resp.status_code == 503
