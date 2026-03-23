from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_subject: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    intent: Mapped[str] = mapped_column(String(64), nullable=False, default="query")
    current_step: Mapped[str] = mapped_column(String(64), nullable=False, default="start")
    last_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_human_input: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_session_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    target_filters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages: Mapped[list["AgentConversationMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AgentConversationMessage.sequence_no",
    )
