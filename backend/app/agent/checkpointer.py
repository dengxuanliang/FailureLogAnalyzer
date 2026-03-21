"""Factory for LangGraph checkpointer backends."""
from __future__ import annotations

from typing import Any

from app.core.config import settings


def create_checkpointer(connection_string: str | None = None) -> Any:
    """Create checkpointer; postgres when available, memory otherwise."""
    if connection_string is None:
        connection_string = getattr(settings, "LANGGRAPH_CHECKPOINTER_URL", None)

    if connection_string and connection_string.startswith("postgres"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            return PostgresSaver.from_conn_string(connection_string)
        except Exception:
            pass

    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()
