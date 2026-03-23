from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.logging_middleware import LoggingMiddleware


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


@pytest.mark.asyncio
async def test_logging_middleware_logs_and_reraises_exceptions() -> None:
    middleware = LoggingMiddleware(app)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/boom",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )

    async def _call_next(_request):
        raise RuntimeError("boom")

    with patch("app.middleware.logging_middleware.logger.error") as mock_error:
        with pytest.raises(RuntimeError, match="boom"):
            await middleware.dispatch(request, _call_next)

    assert mock_error.call_count == 1
    args, kwargs = mock_error.call_args
    assert args == ("unhandled_exception",)
    assert kwargs["error"] == "boom"
    assert "RuntimeError: boom" in kwargs["traceback"]
