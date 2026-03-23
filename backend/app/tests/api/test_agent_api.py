"""Tests for the Agent conversation REST API."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.main import app
from app.schemas.agent import AgentMessage, ConversationListItem


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-analyst-token"}


@pytest.fixture
def fake_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def bypass_auth_and_db(fake_db: AsyncMock):
    async def _fake_user():
        return SimpleNamespace(role="viewer", is_active=True, username="tester")

    async def _fake_db():
        yield fake_db

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_db] = _fake_db
    try:
        yield fake_db
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_agent_chat_new_conversation_persists(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    bypass_auth_and_db,
) -> None:
    with (
        patch("app.api.v1.routers.agent.get_graph") as mock_get_graph,
        patch("app.api.v1.routers.agent._persist_conversation", new_callable=AsyncMock) as mock_persist,
    ):
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "user_input": "查看概览",
                "intent": "query",
                "conversation_history": [
                    {"role": "user", "content": "查看概览"},
                    {"role": "assistant", "content": "分析概览:\n- 评测批次: 5"},
                ],
                "current_step": "query_done",
                "needs_human_input": False,
            }
        )
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
    assert len(data["messages"]) == 2
    mock_persist.assert_awaited_once()
    persisted_conversation_id = mock_persist.await_args.kwargs["conversation_id"]
    assert persisted_conversation_id == data["conversation_id"]


@pytest.mark.asyncio
async def test_agent_chat_with_existing_conversation_resumes_from_history(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    bypass_auth_and_db,
) -> None:
    old_messages = [
        AgentMessage(
            id="msg-1",
            role="user",
            content="查看概览",
            timestamp=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
        ),
        AgentMessage(
            id="msg-2",
            role="assistant",
            content="分析概览:\n- 评测批次: 5",
            timestamp=datetime(2026, 3, 23, 8, 0, 1, tzinfo=timezone.utc),
        ),
    ]
    existing_conversation = SimpleNamespace(
        conversation_id="conv-existing-123",
        target_session_ids=["session-1"],
        target_filters={"benchmark": "mmlu"},
        intent="query",
        current_step="query_done",
        needs_human_input=False,
        created_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 23, 8, 0, 1, tzinfo=timezone.utc),
    )

    with (
        patch("app.api.v1.routers.agent.get_graph") as mock_get_graph,
        patch("app.api.v1.routers.agent._load_conversation", new_callable=AsyncMock) as mock_load,
        patch("app.api.v1.routers.agent._persist_conversation", new_callable=AsyncMock) as mock_persist,
    ):
        mock_load.return_value = (existing_conversation, old_messages)

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "user_input": "错误分布",
                "intent": "query",
                "conversation_history": [
                    {"role": "user", "content": "查看概览"},
                    {"role": "assistant", "content": "分析概览:\n- 评测批次: 5"},
                    {"role": "user", "content": "错误分布"},
                    {"role": "assistant", "content": "错误分布:"},
                ],
                "current_step": "query_done",
                "needs_human_input": False,
            }
        )
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
    assert len(data["messages"]) == 4

    ainvoke_state = mock_get_graph.return_value.ainvoke.await_args.args[0]
    assert ainvoke_state["conversation_history"] == [
        {"role": "user", "content": "查看概览"},
        {"role": "assistant", "content": "分析概览:\n- 评测批次: 5"},
    ]
    assert ainvoke_state["target_session_ids"] == ["session-1"]
    assert ainvoke_state["target_filters"] == {"benchmark": "mmlu"}

    mock_load.assert_awaited_once()
    mock_persist.assert_awaited_once()
    assert mock_persist.await_args.kwargs["target_session_ids"] == ["session-1"]
    assert mock_persist.await_args.kwargs["target_filters"] == {"benchmark": "mmlu"}


@pytest.mark.asyncio
async def test_list_conversations(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    bypass_auth_and_db,
) -> None:
    with patch("app.api.v1.routers.agent._list_conversation_items", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [
            ConversationListItem(
                conversation_id="conv-1",
                last_message="分析概览",
                intent="query",
                current_step="query_done",
                updated_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
            )
        ]

        resp = await async_client.get(
            "/api/v1/agent/conversations",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload == [
        {
            "conversation_id": "conv-1",
            "last_message": "分析概览",
            "intent": "query",
            "current_step": "query_done",
            "updated_at": "2026-03-23T08:00:00Z",
        }
    ]
    mock_list.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_conversation_detail_with_history(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    bypass_auth_and_db,
) -> None:
    conversation = SimpleNamespace(
        conversation_id="conv-1",
        intent="query",
        current_step="query_done",
        needs_human_input=False,
        created_at=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 23, 8, 1, tzinfo=timezone.utc),
    )
    messages = [
        AgentMessage(
            id="msg-1",
            role="user",
            content="查看概览",
            timestamp=datetime(2026, 3, 23, 8, 0, tzinfo=timezone.utc),
        ),
        AgentMessage(
            id="msg-2",
            role="assistant",
            content="分析概览:\n- 评测批次: 5",
            timestamp=datetime(2026, 3, 23, 8, 0, 1, tzinfo=timezone.utc),
        ),
    ]

    with patch("app.api.v1.routers.agent._load_conversation", new_callable=AsyncMock) as mock_load:
        mock_load.return_value = (conversation, messages)

        resp = await async_client.get(
            "/api/v1/agent/conversations/conv-1",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["conversation_id"] == "conv-1"
    assert payload["intent"] == "query"
    assert payload["current_step"] == "query_done"
    assert payload["reply"] == "分析概览:\n- 评测批次: 5"
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["id"] == "msg-1"


@pytest.mark.asyncio
async def test_get_conversation_detail_returns_404_when_missing(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    bypass_auth_and_db,
) -> None:
    with patch("app.api.v1.routers.agent._load_conversation", new_callable=AsyncMock) as mock_load:
        mock_load.return_value = None

        resp = await async_client.get(
            "/api/v1/agent/conversations/missing",
            headers=auth_headers,
        )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Conversation not found"


@pytest.mark.asyncio
async def test_agent_chat_requires_auth(async_client: AsyncClient) -> None:
    resp = await async_client.post(
        "/api/v1/agent/chat",
        json={"message": "hello"},
    )
    assert resp.status_code in (401, 403)
