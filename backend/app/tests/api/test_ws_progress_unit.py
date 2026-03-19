import pytest
import orjson
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi.websockets import WebSocket


@pytest.mark.asyncio
async def test_progress_router_relays_redis_message():
    """Unit test: verify the router reads from pubsub and forwards to WS."""
    from app.api.v1.ws_progress import relay_progress

    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()
    mock_ws.receive_text = AsyncMock(side_effect=Exception("disconnect"))

    fake_message = {"type": "message", "data": orjson.dumps({"processed": 100, "status": "running"})}

    mock_pubsub = AsyncMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.listen = AsyncMock(return_value=_async_gen([fake_message]))
    mock_pubsub.unsubscribe = AsyncMock()

    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    with patch("app.api.v1.ws_progress.get_redis", AsyncMock(return_value=mock_redis)):
        await relay_progress(mock_ws, job_id="test-job")

    mock_ws.send_text.assert_called()
    # First call is the "connected" event, second may be the message
    calls = mock_ws.send_text.call_args_list
    assert len(calls) >= 1
    # Check that one of the calls contains processed=100
    payloads = [orjson.loads(c[0][0]) for c in calls]
    processed_payloads = [p for p in payloads if p.get("processed") == 100]
    assert len(processed_payloads) >= 1


async def _async_gen(items):
    for item in items:
        yield item
