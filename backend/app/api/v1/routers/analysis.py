from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db.models.enums import UserRole
from app.db.session import get_db
from app.schemas.analysis_query import (
    AnalysisSummary,
    DistributionItem,
    PaginatedRecords,
    RecordDetail,
    RecordTagsPatchRequest,
    RecordTagsPatchResponse,
)
from app.services.analysis_query import (
    get_analysis_summary,
    get_error_distribution,
    get_error_records_page,
    get_record_detail,
    update_record_error_tags,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/summary", response_model=AnalysisSummary)
async def analysis_summary(
    benchmark: str | None = None,
    model_version: str | None = None,
    time_range_start: datetime | None = None,
    time_range_end: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    return await get_analysis_summary(
        db=db,
        benchmark=benchmark,
        model_version=model_version,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
    )


@router.get("/error-distribution", response_model=list[DistributionItem])
async def error_distribution(
    group_by: str = Query(..., pattern=r"^(error_type|category|severity)$"),
    benchmark: str | None = None,
    model_version: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    return await get_error_distribution(
        db=db,
        group_by=group_by,
        benchmark=benchmark,
        model_version=model_version,
    )


@router.get("/records", response_model=PaginatedRecords)
async def error_records(
    error_type: str | None = None,
    benchmark: str | None = None,
    model_version: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    return await get_error_records_page(
        db=db,
        error_type=error_type,
        benchmark=benchmark,
        model_version=model_version,
        page=page,
        size=size,
    )


@router.get("/records/{record_id}/detail", response_model=RecordDetail)
async def record_detail(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    detail = await get_record_detail(db=db, record_id=record_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return detail


@router.patch("/records/{record_id}/tags", response_model=RecordTagsPatchResponse)
async def patch_record_tags(
    record_id: uuid.UUID,
    payload: RecordTagsPatchRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.analyst)),
):
    result = await update_record_error_tags(db=db, record_id=record_id, tags=payload.tags)
    if result is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return result
