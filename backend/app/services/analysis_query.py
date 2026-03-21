from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis_result import AnalysisResult
from app.db.models.enums import AnalysisType
from app.db.models.error_tag import ErrorTag
from app.db.models.eval_record import EvalRecord
from app.db.models.eval_session import EvalSession


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _build_session_filters(
    benchmark: str | None,
    model_version: str | None,
    time_range_start: datetime | None,
    time_range_end: datetime | None,
) -> list[Any]:
    filters: list[Any] = []
    if benchmark:
        filters.append(EvalSession.benchmark == benchmark)
    if model_version:
        filters.append(EvalSession.model_version == model_version)
    if time_range_start:
        filters.append(EvalSession.created_at >= time_range_start)
    if time_range_end:
        filters.append(EvalSession.created_at <= time_range_end)
    return filters


async def get_analysis_summary(
    db: AsyncSession,
    benchmark: str | None,
    model_version: str | None,
    time_range_start: datetime | None,
    time_range_end: datetime | None,
) -> dict[str, Any]:
    session_stmt = select(EvalSession).where(
        *_build_session_filters(benchmark, model_version, time_range_start, time_range_end)
    )
    sessions = (await db.execute(session_stmt)).scalars().all()

    total_sessions = len(sessions)
    total_records = sum(int(s.total_count or 0) for s in sessions)
    total_errors = sum(int(s.error_count or 0) for s in sessions)
    weighted_correct = sum(float(s.accuracy or 0.0) * int(s.total_count or 0) for s in sessions)
    accuracy = (weighted_correct / total_records) if total_records else 0.0

    session_ids = [s.id for s in sessions]
    if session_ids:
        llm_stmt = (
            select(
                func.count(AnalysisResult.id),
                func.coalesce(func.sum(AnalysisResult.llm_cost), 0.0),
            )
            .join(EvalRecord, EvalRecord.id == AnalysisResult.record_id)
            .where(
                EvalRecord.session_id.in_(session_ids),
                AnalysisResult.analysis_type == AnalysisType.llm,
            )
        )
        llm_count, llm_cost = (await db.execute(llm_stmt)).one()
    else:
        llm_count, llm_cost = 0, 0.0

    return {
        "total_sessions": total_sessions,
        "total_records": total_records,
        "total_errors": total_errors,
        "accuracy": round(float(accuracy), 4),
        "llm_analysed_count": int(llm_count or 0),
        "llm_total_cost": round(float(llm_cost or 0.0), 6),
    }


async def get_error_distribution(
    db: AsyncSession,
    group_by: str,
    benchmark: str | None,
    model_version: str | None,
) -> list[dict[str, Any]]:
    filters: list[Any] = []
    if benchmark:
        filters.append(EvalRecord.benchmark == benchmark)
    if model_version:
        filters.append(EvalSession.model_version == model_version)

    if group_by == "error_type":
        label_expr = func.split_part(ErrorTag.tag_path, ".", 1)
        stmt = (
            select(label_expr.label("label"), func.count(ErrorTag.id).label("cnt"))
            .select_from(ErrorTag)
            .join(EvalRecord, EvalRecord.id == ErrorTag.record_id)
            .join(EvalSession, EvalSession.id == EvalRecord.session_id)
            .where(*filters)
            .group_by(label_expr)
            .order_by(func.count(ErrorTag.id).desc())
        )
    elif group_by == "category":
        stmt = (
            select(EvalRecord.task_category.label("label"), func.count(ErrorTag.id).label("cnt"))
            .select_from(ErrorTag)
            .join(EvalRecord, EvalRecord.id == ErrorTag.record_id)
            .join(EvalSession, EvalSession.id == EvalRecord.session_id)
            .where(*filters)
            .group_by(EvalRecord.task_category)
            .order_by(func.count(ErrorTag.id).desc())
        )
    elif group_by == "severity":
        stmt = (
            select(AnalysisResult.severity.label("label"), func.count(ErrorTag.id).label("cnt"))
            .select_from(ErrorTag)
            .join(EvalRecord, EvalRecord.id == ErrorTag.record_id)
            .join(EvalSession, EvalSession.id == EvalRecord.session_id)
            .join(AnalysisResult, AnalysisResult.id == ErrorTag.analysis_result_id)
            .where(*filters)
            .group_by(AnalysisResult.severity)
            .order_by(func.count(ErrorTag.id).desc())
        )
    else:
        raise ValueError("group_by must be one of: error_type, category, severity")

    rows = (await db.execute(stmt)).all()
    total = sum(int(r.cnt) for r in rows) if rows else 0
    return [
        {
            "label": str(_enum_value(r.label) or "(unknown)"),
            "count": int(r.cnt),
            "percentage": round((float(r.cnt) / total * 100.0), 2) if total else 0.0,
        }
        for r in rows
    ]


async def get_error_records_page(
    db: AsyncSession,
    error_type: str | None,
    benchmark: str | None,
    model_version: str | None,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    filters: list[Any] = [EvalRecord.is_correct.is_(False)]
    if benchmark:
        filters.append(EvalRecord.benchmark == benchmark)
    if model_version:
        filters.append(EvalSession.model_version == model_version)

    if error_type:
        tag_subquery = select(ErrorTag.record_id).where(ErrorTag.tag_path.like(f"{error_type}%"))
        filters.append(EvalRecord.id.in_(tag_subquery))

    filtered_stmt = (
        select(EvalRecord)
        .join(EvalSession, EvalSession.id == EvalRecord.session_id)
        .where(and_(*filters))
    )

    total_stmt = select(func.count()).select_from(filtered_stmt.subquery())
    total = int((await db.execute(total_stmt)).scalar_one())

    rows = (
        await db.execute(
            filtered_stmt
            .order_by(EvalRecord.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).scalars().all()

    items: list[dict[str, Any]] = []
    for rec in rows:
        tags_stmt = select(ErrorTag.tag_path).where(ErrorTag.record_id == rec.id)
        tags = [row[0] for row in (await db.execute(tags_stmt)).all()]

        llm_exists_stmt = select(func.count(AnalysisResult.id)).where(
            AnalysisResult.record_id == rec.id,
            AnalysisResult.analysis_type == AnalysisType.llm,
        )
        has_llm_analysis = int((await db.execute(llm_exists_stmt)).scalar_one() or 0) > 0

        items.append(
            {
                "id": rec.id,
                "session_id": rec.session_id,
                "benchmark": rec.benchmark,
                "task_category": rec.task_category,
                "question_id": rec.question_id,
                "question": rec.question or "",
                "is_correct": bool(rec.is_correct),
                "score": rec.score,
                "error_tags": tags,
                "has_llm_analysis": has_llm_analysis,
            }
        )

    return {"items": items, "total": total, "page": page, "size": size}


async def get_record_detail(db: AsyncSession, record_id: uuid.UUID) -> dict[str, Any] | None:
    record = await db.get(EvalRecord, record_id)
    if record is None:
        return None

    analysis_rows = (
        await db.execute(
            select(AnalysisResult)
            .where(AnalysisResult.record_id == record_id)
            .order_by(AnalysisResult.created_at.asc())
        )
    ).scalars().all()

    tag_rows = (
        await db.execute(
            select(ErrorTag)
            .where(ErrorTag.record_id == record_id)
            .order_by(ErrorTag.created_at.asc())
        )
    ).scalars().all()

    return {
        "record": {
            "id": record.id,
            "session_id": record.session_id,
            "benchmark": record.benchmark,
            "task_category": record.task_category,
            "question_id": record.question_id,
            "question": record.question,
            "expected_answer": record.expected_answer,
            "model_answer": record.model_answer,
            "is_correct": record.is_correct,
            "score": record.score,
            "created_at": record.created_at,
        },
        "analysis_results": [
            {
                "id": row.id,
                "analysis_type": str(_enum_value(row.analysis_type)),
                "error_types": list(row.error_types or []),
                "root_cause": row.root_cause,
                "severity": _enum_value(row.severity),
                "confidence": row.confidence,
                "evidence": row.evidence,
                "suggestion": row.suggestion,
                "llm_model": row.llm_model,
                "llm_cost": row.llm_cost,
                "unmatched_tags": list(row.unmatched_tags or []),
                "created_at": row.created_at,
            }
            for row in analysis_rows
        ],
        "error_tags": [
            {
                "id": tag.id,
                "analysis_result_id": tag.analysis_result_id,
                "tag_path": tag.tag_path,
                "tag_level": tag.tag_level,
                "source": str(_enum_value(tag.source)),
                "confidence": tag.confidence,
                "created_at": tag.created_at,
            }
            for tag in tag_rows
        ],
    }
