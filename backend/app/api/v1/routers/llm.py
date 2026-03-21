"""LLM strategy/template CRUD and job orchestration endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_role
from app.core.redis import get_redis
from app.db.models.analysis_result import AnalysisResult
from app.db.models.analysis_strategy import AnalysisStrategy
from app.db.models.enums import AnalysisType, UserRole
from app.db.models.eval_record import EvalRecord
from app.db.models.eval_session import EvalSession
from app.db.models.prompt_template import PromptTemplate
from app.db.models.user import User
from app.db.session import get_db
from app.llm.job_store import create_job, get_job_status, update_job
from app.schemas.llm import (
    LlmJobStatusResponse,
    LlmJobTriggerRequest,
    LlmJobTriggerResponse,
    SessionCostModelBreakdown,
    SessionCostSummaryResponse,
    StrategyCreate,
    StrategyPatch,
    StrategyResponse,
    TemplateCreate,
    TemplatePatch,
    TemplateResponse,
)
from app.tasks.analysis import run_llm_judge

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await db.execute(select(PromptTemplate).order_by(PromptTemplate.created_at.desc()))
    return rows.scalars().all()


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    template = await db.get(PromptTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.analyst)),
):
    template = PromptTemplate(**payload.model_dump(), created_by=current_user.username)
    db.add(template)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"Create template failed: {exc}")
    await db.refresh(template)
    return template


@router.patch("/templates/{template_id}", response_model=TemplateResponse)
async def patch_template(
    template_id: uuid.UUID,
    payload: TemplatePatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.analyst)),
):
    template = await db.get(PromptTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, key, value)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.analyst)),
):
    template = await db.get(PromptTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(template)
    await db.commit()


@router.get("/strategies", response_model=list[StrategyResponse])
async def list_strategies(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await db.execute(select(AnalysisStrategy).order_by(AnalysisStrategy.created_at.desc()))
    return rows.scalars().all()


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    strategy = await db.get(AnalysisStrategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.post("/strategies", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    payload: StrategyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.analyst)),
):
    if payload.prompt_template_id is not None:
        template = await db.get(PromptTemplate, payload.prompt_template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Prompt template not found")

    strategy = AnalysisStrategy(**payload.model_dump(), created_by=current_user.username)
    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)
    return strategy


@router.patch("/strategies/{strategy_id}", response_model=StrategyResponse)
async def patch_strategy(
    strategy_id: uuid.UUID,
    payload: StrategyPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.analyst)),
):
    strategy = await db.get(AnalysisStrategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    updates = payload.model_dump(exclude_unset=True)
    prompt_template_id = updates.get("prompt_template_id")
    if prompt_template_id is not None:
        template = await db.get(PromptTemplate, prompt_template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Prompt template not found")

    for key, value in updates.items():
        setattr(strategy, key, value)

    await db.commit()
    await db.refresh(strategy)
    return strategy


@router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.analyst)),
):
    strategy = await db.get(AnalysisStrategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await db.delete(strategy)
    await db.commit()


@router.post("/jobs/trigger", response_model=LlmJobTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_llm_job(
    payload: LlmJobTriggerRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.analyst)),
):
    session = await db.get(EvalSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    strategy = await db.get(AnalysisStrategy, payload.strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if not strategy.is_active:
        raise HTTPException(status_code=409, detail="Strategy is inactive")

    job_id = str(uuid.uuid4())
    redis = await get_redis()
    manual_ids = [str(item) for item in payload.manual_record_ids]
    await create_job(
        redis,
        job_id=job_id,
        session_id=str(payload.session_id),
        strategy_id=str(payload.strategy_id),
        manual_record_ids=manual_ids,
    )

    task = run_llm_judge.delay(
        session_id=str(payload.session_id),
        strategy_id=str(payload.strategy_id),
        job_id=job_id,
        manual_record_ids=manual_ids,
    )
    await update_job(redis, job_id, celery_task_id=task.id, status="queued")

    return LlmJobTriggerResponse(job_id=job_id, celery_task_id=task.id, status="queued")


@router.get("/jobs/{job_id}/status", response_model=LlmJobStatusResponse)
async def get_llm_job_status(
    job_id: str,
    _: User = Depends(get_current_user),
):
    redis = await get_redis()
    payload = await get_job_status(redis, job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return LlmJobStatusResponse(**payload)


@router.get("/sessions/{session_id}/cost-summary", response_model=SessionCostSummaryResponse)
async def get_session_cost_summary(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    session = await db.get(EvalSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    stmt = (
        select(
            AnalysisResult.llm_model,
            sqlfunc.count(AnalysisResult.id),
            sqlfunc.coalesce(sqlfunc.sum(AnalysisResult.llm_cost), 0.0),
        )
        .join(EvalRecord, EvalRecord.id == AnalysisResult.record_id)
        .where(EvalRecord.session_id == session_id)
        .where(AnalysisResult.analysis_type == AnalysisType.llm)
        .group_by(AnalysisResult.llm_model)
        .order_by(sqlfunc.coalesce(sqlfunc.sum(AnalysisResult.llm_cost), 0.0).desc())
    )
    rows = (await db.execute(stmt)).all()

    breakdown: list[SessionCostModelBreakdown] = []
    total_calls = 0
    total_cost = 0.0
    for llm_model, calls, model_cost in rows:
        calls_int = int(calls or 0)
        cost_float = float(model_cost or 0.0)
        breakdown.append(
            SessionCostModelBreakdown(
                llm_model=llm_model or "",
                calls=calls_int,
                total_cost=cost_float,
            )
        )
        total_calls += calls_int
        total_cost += cost_float

    return SessionCostSummaryResponse(
        session_id=str(session_id),
        total_calls=total_calls,
        total_cost=total_cost,
        by_model=breakdown,
    )
