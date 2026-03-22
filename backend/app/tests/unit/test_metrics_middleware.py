from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY

from app.main import app


def _get_sample_count(sample_name: str) -> float:
    total = 0.0
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == sample_name:
                total += sample.value
    return total


@pytest.mark.asyncio
async def test_http_histogram_incremented_on_request() -> None:
    before = _get_sample_count("fla_http_request_duration_seconds_count")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.api.v1.routers.health.check_db", AsyncMock(return_value=True)), patch(
            "app.api.v1.routers.health.check_redis", AsyncMock(return_value=True)
        ):
            await client.get("/api/v1/health")

    after = _get_sample_count("fla_http_request_duration_seconds_count")
    assert after > before
