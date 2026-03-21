"""Tests for the Agent conversation REST API."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.main import app


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-analyst-token"}


@pytest.fixture
def bypass_auth_and_db():
    async def _fake_user():
        return SimpleNamespace(role="viewer", is_active=True)

    async def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_db] = _fake_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_agent_chat_new_conversation(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    bypass_auth_and_db,
) -> None:
    with patch("app.api.v1.routers.agent.get_graph") as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "user_input": "查看概览",
            "intent": "query",
            "conversation_history": [
                {"role": "user", "content": "查看概览"},
                {"role": "assistant", "content": "分析概览:\n- 评测批次: 5"},
            ],
            "current_step": "query_done",
            "needs_human_input": False,
        })
        mock_get_graph.return_value = mock_graph

        resp = await async_client.post(
            "/api/v1/agent/chat",
            json={"message": "查看概览"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "conversation_id" in data
    assert data["intent"] == "query"
    assert len(data["messages"]) >= 1


@pytest.mark.asyncio
async def test_agent_chat_with_existing_conversation(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    bypass_auth_and_db,
) -> None:
    with patch("app.api.v1.routers.agent.get_graph") as mock_get_graph:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "user_input": "错误分布",
            "intent": "query",
            "conversation_history": [
                {"role": "user", "content": "错误分布"},
                {"role": "assistant", "content": "错误分布:"},
            ],
            "current_step": "query_done",
            "needs_human_input": False,
        })
        mock_get_graph.return_value = mock_graph

        resp = await async_client.post(
            "/api/v1/agent/chat",
            json={
                "message": "错误分布",
                "conversation_id": "conv-existing-123",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["conversation_id"] == "conv-existing-123"


@pytest.mark.asyncio
async def test_agent_chat_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/api/v1/agent/chat",
        json={"message": "hello"},
    )
    assert resp.status_code in (401, 403)
