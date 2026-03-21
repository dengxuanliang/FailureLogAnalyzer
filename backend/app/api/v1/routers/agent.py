"""Agent conversation REST + WebSocket API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import build_graph
from app.agent.state import create_initial_state
from app.api.v1.deps import require_role
from app.db.models.enums import UserRole
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentMessage

router = APIRouter(prefix="/agent", tags=["agent"])

_graph = None


def get_graph():
    """Return singleton compiled graph."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_role(UserRole.viewer)),
) -> AgentChatResponse:
    """Send one message to orchestrator and return current conversation state."""
    _ = current_user
    conv_id = payload.conversation_id or str(uuid.uuid4())

    state = create_initial_state(user_input=payload.message)
    if payload.session_ids:
        state["target_session_ids"] = payload.session_ids
    if payload.filters:
        state["target_filters"].update(payload.filters)

    graph = get_graph()
    result = graph.invoke(
        state,
        config={"configurable": {"thread_id": conv_id, "db": db}},
    )

    messages = [
        AgentMessage(
            role=m["role"],
            content=m["content"],
            timestamp=datetime.now(timezone.utc),
        )
        for m in result.get("conversation_history", [])
    ]

    return AgentChatResponse(
        conversation_id=conv_id,
        messages=messages,
        current_step=result.get("current_step", ""),
        intent=result.get("intent", ""),
        needs_human_input=result.get("needs_human_input", False),
    )


@router.websocket("/ws")
async def agent_websocket(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """WebSocket endpoint for streaming orchestrator interactions."""
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    await websocket.accept()
    conv_id = str(uuid.uuid4())

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            conv_id = data.get("conversation_id", conv_id)

            state = create_initial_state(user_input=message)
            if data.get("session_ids"):
                state["target_session_ids"] = data["session_ids"]
            if data.get("filters"):
                state["target_filters"].update(data["filters"])

            await websocket.send_json(
                {"type": "step", "data": {"step": "routing", "intent": ""}}
            )

            async with AsyncSessionLocal() as db:
                graph = get_graph()
                result = graph.invoke(
                    state,
                    config={"configurable": {"thread_id": conv_id, "db": db}},
                )

            messages = [
                {"role": m["role"], "content": m["content"]}
                for m in result.get("conversation_history", [])
            ]

            await websocket.send_json(
                {
                    "type": "message",
                    "data": {
                        "conversation_id": conv_id,
                        "messages": messages,
                        "current_step": result.get("current_step", ""),
                        "intent": result.get("intent", ""),
                        "needs_human_input": result.get("needs_human_input", False),
                    },
                }
            )
    except WebSocketDisconnect:
        return
