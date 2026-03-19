from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.db.engine import engine

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

@asynccontextmanager
async def get_async_session() -> AsyncSession:
    """Async context manager for use in Celery tasks and other non-dependency contexts."""
    async with AsyncSessionLocal() as session:
        yield session
