"""Pydantic schemas for the Agent conversation API."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: str | None = None
    session_ids: list[str] | None = None
    filters: dict[str, Any] | None = None


class AgentMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime | None = None


class AgentChatResponse(BaseModel):
    conversation_id: str
    messages: list[AgentMessage]
    current_step: str
    intent: str
    needs_human_input: bool = False


class ConversationListItem(BaseModel):
    conversation_id: str
    last_message: str
    intent: str
    current_step: str
    updated_at: datetime
