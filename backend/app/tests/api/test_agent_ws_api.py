from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class _DummyGraph:
    async def ainvoke(self, _state, config=None):
        return {
            "conversation_history": [
                {"role": "user", "content": "show compare"},
                {"role": "assistant", "content": "Opening compare view."},
            ],
            "current_step": "query_done",
            "intent": "compare",
            "needs_human_input": False,
        }


def test_agent_websocket_spec_route_streams_frontend_compatible_message():
    with patch("app.api.v1.routers.agent.get_graph", return_value=_DummyGraph()):
        client = TestClient(app)
        with client.websocket_connect("/api/v1/ws/agent?token=test-token") as websocket:
            websocket.send_json(
                {
                    "message": "show compare",
                    "conversation_id": "conv-1",
                    "filters": {"benchmark": "mmlu"},
                }
            )
            payload = websocket.receive_json()

    assert payload["type"] == "message"
    assert payload["conversation_id"] == "conv-1"
    assert payload["message"]["role"] == "assistant"
    assert payload["message"]["content"] == "Opening compare view."
    datetime.fromisoformat(payload["message"]["timestamp"].replace("Z", "+00:00")).astimezone(
        timezone.utc
    )
