from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.engine import engine

def test_engine_is_async():
    assert isinstance(engine, AsyncEngine)

def test_engine_url_contains_asyncpg():
    assert "asyncpg" in str(engine.url)
