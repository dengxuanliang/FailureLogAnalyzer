from __future__ import annotations
import logging
import orjson
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from app.core.redis import get_redis

logger = logging.getLogger(__name__)
router = APIRouter()

_PROGRESS_CHANNEL_PREFIX = "progress"


async def relay_progress(websocket: WebSocket, job_id: str) -> None:
    """Subscribe to Redis channel and relay messages to WebSocket client."""
    await websocket.accept()
    redis = await get_redis()
    pubsub = redis.pubsub()
    channel = f"{_PROGRESS_CHANNEL_PREFIX}:{job_id}"

    try:
        await pubsub.subscribe(channel)
        await websocket.send_text(
            orjson.dumps({"status": "connected", "job_id": job_id}).decode()
        )
        # pubsub.listen() may be an async generator or an awaitable returning one
        listen_result = pubsub.listen()
        if hasattr(listen_result, "__aiter__"):
            # Direct async generator (real redis)
            stream = listen_result
        else:
            # Awaitable returning async generator (e.g. AsyncMock in tests)
            stream = await listen_result
        async for message in stream:
            if message["type"] != "message":
                continue
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode()
            await websocket.send_text(data)
            # Check if job is done or failed — close gracefully
            try:
                parsed = orjson.loads(data)
                if parsed.get("status") in ("done", "failed"):
                    break
            except Exception:
                pass
    except WebSocketDisconnect:
        logger.debug("WS client disconnected for job %s", job_id)
    except Exception as exc:
        logger.exception("WS relay error for job %s: %s", job_id, exc)
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(
                    orjson.dumps({"status": "error", "reason": str(exc)}).decode()
                )
        except Exception:
            pass
    finally:
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            pass
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/progress")
async def ws_progress_endpoint(
    websocket: WebSocket,
    job_id: str = Query(..., description="Ingest or analysis job ID to subscribe to"),
) -> None:
    """
    WebSocket: WS /api/v1/ws/progress?job_id=<id>

    Streams real-time progress events for an ingest or LLM analysis job.
    Closes automatically when status becomes 'done' or 'failed'.
    """
    await relay_progress(websocket, job_id=job_id)
