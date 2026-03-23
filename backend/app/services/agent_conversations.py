from __future__ import annotations

import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_conversation import AgentConversation
from app.db.models.agent_conversation_message import AgentConversationMessage
from app.schemas.agent import AgentMessage, ConversationListItem


ConversationLike = AgentConversation | SimpleNamespace


async def _resolve(value):
    if inspect.isawaitable(value):
        return await value
    return value


def get_user_subject(current_user: Any) -> str | None:
    for attr in ("id", "username", "email"):
        value = getattr(current_user, attr, None)
        if value:
            return str(value)
    return None


async def _load_conversation(
    db: AsyncSession,
    *,
    conversation_id: str,
    current_user: Any,
) -> tuple[ConversationLike, list[AgentMessage]] | None:
    subject = get_user_subject(current_user)
    stmt = select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
    if subject:
        stmt = stmt.where(AgentConversation.owner_subject == subject)
    result = await _resolve(db.execute(stmt))
    conversation = await _resolve(result.scalar_one_or_none())
    if conversation is None or not hasattr(conversation, "conversation_id"):
        return None

    message_result = await _resolve(
        db.execute(
            select(AgentConversationMessage)
            .where(AgentConversationMessage.conversation_id == conversation_id)
            .order_by(AgentConversationMessage.sequence_no.asc())
        )
    )
    scalars = await _resolve(message_result.scalars())
    rows = list(await _resolve(scalars.all()))
    messages = [
        AgentMessage(
            id=str(row.id),
            role=row.role,
            content=row.content,
            timestamp=row.created_at,
            action=row.action,
        )
        for row in rows
    ]
    return conversation, messages


async def _persist_conversation(
    db: AsyncSession,
    *,
    conversation_id: str,
    current_user: Any,
    messages: list[AgentMessage],
    intent: str,
    current_step: str,
    needs_human_input: bool,
    target_session_ids: list[str],
    target_filters: dict[str, Any],
) -> None:
    subject = get_user_subject(current_user)
    result = await _resolve(
        db.execute(
            select(AgentConversation).where(AgentConversation.conversation_id == conversation_id)
        )
    )
    conversation = await _resolve(result.scalar_one_or_none())
    now = datetime.now(timezone.utc)
    last_message = next((message.content for message in reversed(messages) if message.content), "")

    if conversation is None:
        conversation = AgentConversation(
            conversation_id=conversation_id,
            owner_subject=subject,
            created_at=now,
        )
        db.add(conversation)

    conversation.owner_subject = subject or conversation.owner_subject
    conversation.intent = intent or "query"
    conversation.current_step = current_step or "start"
    conversation.last_message = last_message
    conversation.needs_human_input = needs_human_input
    conversation.target_session_ids = list(target_session_ids)
    conversation.target_filters = dict(target_filters)
    conversation.updated_at = now

    await _resolve(
        db.execute(
            delete(AgentConversationMessage).where(
                AgentConversationMessage.conversation_id == conversation_id
            )
        )
    )

    for index, message in enumerate(messages):
        created_at = message.timestamp or now
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        db.add(
            AgentConversationMessage(
                conversation_id=conversation_id,
                sequence_no=index,
                role=message.role,
                content=message.content,
                action=message.action,
                created_at=created_at,
            )
        )

    await _resolve(db.commit())


async def _list_conversation_items(
    db: AsyncSession,
    *,
    current_user: Any,
    limit: int = 50,
) -> list[ConversationListItem]:
    subject = get_user_subject(current_user)
    stmt = select(AgentConversation).order_by(desc(AgentConversation.updated_at)).limit(limit)
    if subject:
        stmt = stmt.where(AgentConversation.owner_subject == subject)
    result = await _resolve(db.execute(stmt))
    scalars = await _resolve(result.scalars())
    rows = list(await _resolve(scalars.all()))
    return [
        ConversationListItem(
            conversation_id=row.conversation_id,
            last_message=row.last_message or "",
            intent=row.intent,
            current_step=row.current_step,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


async def get_agent_conversation(
    db: AsyncSession,
    *,
    conversation_id: str,
    current_user: Any,
):
    return await _load_conversation(db, conversation_id=conversation_id, current_user=current_user)


async def list_agent_conversations(
    db: AsyncSession,
    *,
    current_user: Any,
    limit: int = 50,
):
    return await _list_conversation_items(db, current_user=current_user, limit=limit)


async def save_agent_conversation_snapshot(
    db: AsyncSession,
    *,
    conversation_id: str,
    current_user: Any,
    messages: list[AgentMessage],
    intent: str,
    current_step: str,
    needs_human_input: bool,
    target_session_ids: list[str],
    target_filters: dict[str, Any],
):
    await _persist_conversation(
        db,
        conversation_id=conversation_id,
        current_user=current_user,
        messages=messages,
        intent=intent,
        current_step=current_step,
        needs_human_input=needs_human_input,
        target_session_ids=target_session_ids,
        target_filters=target_filters,
    )
