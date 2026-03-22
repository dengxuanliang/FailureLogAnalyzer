import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://fla:fla@localhost/fla_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-characters-long")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def async_client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
