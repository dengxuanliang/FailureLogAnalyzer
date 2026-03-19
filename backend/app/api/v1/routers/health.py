from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
import redis.asyncio as aioredis
from app.db.engine import engine
from app.core.config import settings

router = APIRouter(tags=["health"])

async def check_db() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

async def check_redis() -> bool:
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        return True
    except Exception:
        return False

@router.get("/health")
async def health_check():
    db_ok = await check_db()
    redis_ok = await check_redis()
    all_ok = db_ok and redis_ok
    payload = {
        "status": "ok" if all_ok else "degraded",
        "checks": {"db": db_ok, "redis": redis_ok},
    }
    return JSONResponse(content=payload, status_code=200 if all_ok else 503)
