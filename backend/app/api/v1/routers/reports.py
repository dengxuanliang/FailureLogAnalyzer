from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db.models.enums import ReportStatus, UserRole
from app.db.models.report import Report
from app.db.session import get_db
from app.schemas.report import ReportGenerateRequest, ReportGenerateResponse, ReportListItem, ReportResponse
from app.tasks.report import generate_report

router = APIRouter(prefix="/reports", tags=["reports"])


def _render_report_markdown(report: Report) -> str:
    content = report.content or {}
    body = json.dumps(content, ensure_ascii=False, indent=2)
    return "\n".join(
        [
            f"# {report.title}",
            "",
            f"- report_type: {report.report_type.value}",
            f"- status: {report.status.value}",
            f"- benchmark: {report.benchmark or ''}",
            f"- model_version: {report.model_version or ''}",
            "",
            "## content",
            "",
            "```json",
            body,
            "```",
            "",
        ]
    )


@router.post("/generate", response_model=ReportGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_report(
    payload: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role(UserRole.analyst)),
):
    report = Report(
        title=payload.title,
        report_type=payload.report_type,
        benchmark=payload.benchmark,
        model_version=payload.model_version,
        session_ids=payload.session_ids,
        time_range_start=payload.time_range_start,
        time_range_end=payload.time_range_end,
        status=ReportStatus.pending,
        created_by=getattr(current_user, "username", None),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    task_config = {
        "title": payload.title,
        "benchmark": payload.benchmark,
        "model_version": payload.model_version,
        "session_ids": [str(sid) for sid in payload.session_ids] if payload.session_ids else None,
        "time_range_start": payload.time_range_start,
        "time_range_end": payload.time_range_end,
        "version_a": payload.version_a,
        "version_b": payload.version_b,
    }

    generate_report.apply_async(
        kwargs={
            "report_id": str(report.id),
            "report_type": payload.report_type.value,
            "config": task_config,
        }
    )

    return ReportGenerateResponse(
        report_id=report.id,
        status=ReportStatus.pending,
        message=f"Report generation dispatched: {payload.title}",
    )


@router.get("", response_model=list[ReportListItem])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    stmt = select(Report).order_by(desc(Report.created_at)).limit(100)
    return (await db.execute(stmt)).scalars().all()


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/export")
async def export_report(
    report_id: uuid.UUID,
    format: str = Query(default="json", pattern="^(json|markdown)$"),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(UserRole.viewer)),
):
    report = await db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    if format == "markdown":
        return Response(
            content=_render_report_markdown(report),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename=\"report-{report_id}.md\"'},
        )

    payload = ReportResponse.model_validate(report).model_dump(mode="json")
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename=\"report-{report_id}.json\"'},
    )
