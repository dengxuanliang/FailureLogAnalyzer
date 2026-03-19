"""CRUD endpoints for /api/v1/rules."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.api.v1.deps import get_current_user, require_role
from app.db.models.analysis_rule import AnalysisRule
from app.db.models.enums import UserRole
from app.db.models.user import User
from app.schemas.rule import RuleCreate, RulePatch, RuleResponse

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(AnalysisRule).order_by(AnalysisRule.priority))
    return result.scalars().all()


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rule = await db.get(AnalysisRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    payload: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.analyst)),
):
    data = payload.model_dump()
    rule = AnalysisRule(
        **data,
        created_by=current_user.username,
    )
    db.add(rule)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=f"Rule name '{payload.name}' already exists")
    await db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
async def replace_rule(
    rule_id: uuid.UUID,
    payload: RuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.analyst)),
):
    rule = await db.get(AnalysisRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    for key, value in payload.model_dump().items():
        setattr(rule, key, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: uuid.UUID,
    payload: RulePatch,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.analyst)),
):
    rule = await db.get(AnalysisRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.analyst)),
):
    rule = await db.get(AnalysisRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
