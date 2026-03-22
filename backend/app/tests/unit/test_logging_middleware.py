from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_request_id_header_added_to_response() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.api.v1.routers.health.check_db", AsyncMock(return_value=True)), patch(
            "app.api.v1.routers.health.check_redis", AsyncMock(return_value=True)
        ):
            response = await client.get(
                "/api/v1/health",
                headers={"X-Request-ID": "test-req-123"},
            )

    assert response.headers.get("X-Request-ID") == "test-req-123"


@pytest.mark.asyncio
async def test_request_id_generated_when_missing() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.api.v1.routers.health.check_db", AsyncMock(return_value=True)), patch(
            "app.api.v1.routers.health.check_redis", AsyncMock(return_value=True)
        ):
            response = await client.get("/api/v1/health")

    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) == 36
