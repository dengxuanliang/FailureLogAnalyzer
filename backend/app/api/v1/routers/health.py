from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
import redis.asyncio as aioredis

from app.celery_app import celery_app
from app.celery_signals import DEFAULT_QUEUE_NAMES, update_worker_online_metrics
from app.db.engine import engine
from app.core.config import settings
from app.core.metrics import CELERY_QUEUE_DEPTH

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


async def check_celery(queue_names: set[str] | tuple[str, ...] = DEFAULT_QUEUE_NAMES) -> dict:
    queue_set = set(queue_names)
    queue_depth: dict[str, int] = {}
    workers_online = 0
    workers_per_queue: dict[str, int] = {queue: 0 for queue in queue_set}

    redis_client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    try:
        for queue in sorted(queue_set):
            depth = int(await redis_client.llen(queue))
            queue_depth[queue] = depth
            CELERY_QUEUE_DEPTH.labels(queue=queue).set(depth)

        inspect = celery_app.control.inspect(timeout=1.0)
        ping = inspect.ping() if inspect else None
        workers_online = len(ping or {})

        active_queues = inspect.active_queues() if inspect else None
        workers_per_queue = update_worker_online_metrics(
            active_queues=active_queues if isinstance(active_queues, dict) else None,
            queue_names=queue_set,
        )

        return {
            "ok": workers_online > 0,
            "workers_online": workers_online,
            "workers_per_queue": workers_per_queue,
            "queue_depth": queue_depth,
        }
    except Exception:
        return {
            "ok": False,
            "workers_online": workers_online,
            "workers_per_queue": workers_per_queue,
            "queue_depth": queue_depth,
        }
    finally:
        await redis_client.aclose()


@router.get("/health")
async def health_check():
    db_ok = await check_db()
    redis_ok = await check_redis()
    celery_status = await check_celery()
    celery_ok = bool(celery_status.get("ok"))
    all_ok = db_ok and redis_ok and celery_ok
    payload = {
        "status": "ok" if all_ok else "degraded",
        "checks": {"db": db_ok, "redis": redis_ok, "celery": celery_ok},
        "celery": celery_status,
    }
    return JSONResponse(content=payload, status_code=200 if all_ok else 503)
