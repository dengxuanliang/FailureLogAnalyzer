from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.models.eval_session import EvalSession
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(tags=["sessions"])


class SessionListItem(BaseModel):
    id: uuid.UUID
    model: str
    model_version: str
    benchmark: str
    dataset_name: str | None
    total_count: int
    error_count: int
    accuracy: float
    tags: list[str]
    created_at: datetime

    model_config = {"protected_namespaces": ()}


@router.get("/sessions", response_model=list[SessionListItem])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SessionListItem]:
    rows = await db.execute(select(EvalSession).order_by(EvalSession.created_at.desc()))
    sessions = rows.scalars().all()
    return [
        SessionListItem(
            id=session.id,
            model=session.model,
            model_version=session.model_version,
            benchmark=session.benchmark,
            dataset_name=session.dataset_name,
            total_count=session.total_count or 0,
            error_count=session.error_count or 0,
            accuracy=session.accuracy or 0.0,
            tags=session.tags or [],
            created_at=session.created_at,
        )
        for session in sessions
    ]
