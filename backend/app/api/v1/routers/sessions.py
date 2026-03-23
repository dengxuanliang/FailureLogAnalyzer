from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.models.eval_session import EvalSession
from app.db.models.user import User
from app.db.session import get_db
from app.tasks.analysis import run_rules

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


class SessionDetailResponse(SessionListItem):
    updated_at: datetime


class SessionDeleteResponse(BaseModel):
    session_id: uuid.UUID
    deleted: bool


class RerunRulesRequest(BaseModel):
    rule_ids: list[str] | None = None


class SessionActionResponse(BaseModel):
    session_id: uuid.UUID
    job_id: str
    message: str


@router.get("/sessions", response_model=list[SessionListItem])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[SessionListItem]:
    rows = await db.execute(select(EvalSession).order_by(EvalSession.created_at.desc()))
    sessions = rows.scalars().all()
    return [_to_session_item(session) for session in sessions]


def _to_session_item(session: EvalSession) -> SessionListItem:
    return SessionListItem(
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


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SessionDetailResponse:
    session = await db.get(EvalSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    base = _to_session_item(session)
    return SessionDetailResponse(**base.model_dump(), updated_at=session.updated_at)


@router.delete("/sessions/{session_id}", response_model=SessionDeleteResponse)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SessionDeleteResponse:
    session = await db.get(EvalSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await db.delete(session)
    await db.commit()
    return SessionDeleteResponse(session_id=session_id, deleted=True)


@router.post(
    "/sessions/{session_id}/actions/rerun-rules",
    response_model=SessionActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def rerun_session_rules(
    session_id: uuid.UUID,
    payload: RerunRulesRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> SessionActionResponse:
    session = await db.get(EvalSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    celery_result = run_rules.delay(str(session_id), payload.rule_ids)
    return SessionActionResponse(
        session_id=session_id,
        job_id=celery_result.id,
        message="Rule rerun task queued",
    )
