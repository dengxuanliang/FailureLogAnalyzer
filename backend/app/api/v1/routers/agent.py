"""Agent conversation REST + WebSocket API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import build_graph
from app.agent.state import create_initial_state
from app.api.v1.deps import require_role
from app.db.models.enums import UserRole
from app.db.session import AsyncSessionLocal, get_db
from app.schemas.agent import AgentChatRequest, AgentChatResponse, AgentMessage, ConversationListItem
from app.services.agent_conversations import (
    _list_conversation_items,
    _load_conversation,
    _persist_conversation,
)

router = APIRouter(prefix="/agent", tags=["agent"])
stream_router = APIRouter(tags=["agent"])

_graph = None


def get_graph():
    """Return singleton compiled graph."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _build_agent_messages(history: list[dict[str, Any]]) -> list[AgentMessage]:
    return [
        AgentMessage(
            id=str(uuid.uuid4()),
            role=message["role"],
            content=message["content"],
            timestamp=datetime.now(timezone.utc),
            action=message.get("action"),
        )
        for message in history
    ]


async def _run_agent_turn(
    *,
    payload: AgentChatRequest,
    db: AsyncSession | None,
    current_user: Any,
) -> AgentChatResponse:
    conv_id = payload.conversation_id or str(uuid.uuid4())

    state = create_initial_state(user_input=payload.message)

    if payload.conversation_id and db is not None:
        loaded = await _load_conversation(db, conversation_id=payload.conversation_id, current_user=current_user)
        if loaded is not None:
            existing_conversation, old_messages = loaded
            state["conversation_history"] = [
                {"role": message.role, "content": message.content} for message in old_messages
            ]
            state["intent"] = getattr(existing_conversation, "intent", "") or ""
            state["current_step"] = getattr(existing_conversation, "current_step", "start") or "start"
            state["needs_human_input"] = bool(
                getattr(existing_conversation, "needs_human_input", False)
            )
            target_session_ids = getattr(existing_conversation, "target_session_ids", None)
            if target_session_ids:
                state["target_session_ids"] = list(target_session_ids)
            target_filters = getattr(existing_conversation, "target_filters", None)
            if target_filters:
                state["target_filters"].update(target_filters)

    if payload.session_ids is not None:
        state["target_session_ids"] = payload.session_ids
    if payload.filters is not None:
        state["target_filters"].update(payload.filters)

    graph = get_graph()
    result = await graph.ainvoke(
        state,
        config={"configurable": {"thread_id": conv_id, "db": db}},
    )

    messages = _build_agent_messages(result.get("conversation_history", []))
    action = result.get("action")
    reply = messages[-1].content if messages else ""

    if db is not None:
        await _persist_conversation(
            db,
            conversation_id=conv_id,
            current_user=current_user,
            messages=messages,
            intent=result.get("intent", "") or "query",
            current_step=result.get("current_step", "") or "start",
            needs_human_input=result.get("needs_human_input", False),
            target_session_ids=list(state.get("target_session_ids", [])),
            target_filters=dict(state.get("target_filters", {})),
        )

    return AgentChatResponse(
        conversation_id=conv_id,
        messages=messages,
        reply=reply,
        action=action,
        current_step=result.get("current_step", ""),
        intent=result.get("intent", ""),
        needs_human_input=result.get("needs_human_input", False),
    )


@router.get("/conversations", response_model=list[ConversationListItem])
async def conversations(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_role(UserRole.viewer)),
) -> list[ConversationListItem]:
    return await _list_conversation_items(db, current_user=current_user)


@router.get("/conversations/{conversation_id}", response_model=AgentChatResponse)
async def conversation_detail(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_role(UserRole.viewer)),
) -> AgentChatResponse:
    loaded = await _load_conversation(db, conversation_id=conversation_id, current_user=current_user)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation, messages = loaded
    action = next((message.action for message in reversed(messages) if message.action is not None), None)
    reply = next((message.content for message in reversed(messages) if message.role == "assistant"), "")
    return AgentChatResponse(
        conversation_id=conversation_id,
        messages=messages,
        reply=reply,
        action=action,
        current_step=getattr(conversation, "current_step", "") or "",
        intent=getattr(conversation, "intent", "") or "",
        needs_human_input=bool(getattr(conversation, "needs_human_input", False)),
    )


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(require_role(UserRole.viewer)),
) -> AgentChatResponse:
    """Send one message to orchestrator and return current conversation state."""
    return await _run_agent_turn(payload=payload, db=db, current_user=current_user)


async def _agent_websocket_impl(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    """WebSocket endpoint for streaming orchestrator interactions."""
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    await websocket.accept()
    conv_id = str(uuid.uuid4())
    websocket_user = {"id": token}

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            conv_id = data.get("conversation_id", conv_id)

            payload = AgentChatRequest(
                message=message,
                conversation_id=conv_id,
                session_ids=data.get("session_ids"),
                filters=data.get("filters"),
            )

            try:
                async with AsyncSessionLocal() as db:
                    response = await _run_agent_turn(payload=payload, db=db, current_user=websocket_user)
            except Exception:
                response = await _run_agent_turn(payload=payload, db=None, current_user=websocket_user)

            assistant_message = next(
                (message for message in reversed(response.messages) if message.role == "assistant"),
                AgentMessage(
                    id=str(uuid.uuid4()),
                    role="assistant",
                    content="",
                    timestamp=datetime.now(timezone.utc),
                ),
            )

            await websocket.send_json(
                {
                    "type": "message",
                    "conversation_id": response.conversation_id,
                    "message": assistant_message.model_dump(mode="json"),
                }
            )
            if response.action is not None:
                await websocket.send_json(
                    {
                        "type": "action",
                        "conversation_id": response.conversation_id,
                        "action": response.action,
                    }
                )
    except WebSocketDisconnect:
        return


@router.websocket("/ws")
async def agent_websocket_legacy(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    await _agent_websocket_impl(websocket, token)


@stream_router.websocket("/ws/agent")
async def agent_websocket(
    websocket: WebSocket,
    token: str | None = Query(None),
) -> None:
    await _agent_websocket_impl(websocket, token)
