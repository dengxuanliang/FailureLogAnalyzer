from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import ReportType
from app.services.analysis_query import get_analysis_summary, get_error_distribution
from app.services.compare import compare_versions, get_radar_data, get_version_diff
from app.services.cross_benchmark import get_benchmark_matrix, get_error_trends, get_systematic_weaknesses


def _to_report_type(value: ReportType | str) -> ReportType:
    if isinstance(value, ReportType):
        return value
    return ReportType(value)


async def build_report(
    db: AsyncSession,
    report_type: ReportType | str,
    config: dict[str, Any],
) -> dict[str, Any]:
    report_kind = _to_report_type(report_type)

    base = {
        "title": config.get("title", "Generated Report"),
        "report_type": report_kind.value,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": config,
    }

    if report_kind == ReportType.summary:
        base["summary"] = await get_analysis_summary(
            db=db,
            benchmark=config.get("benchmark"),
            model_version=config.get("model_version"),
            time_range_start=config.get("time_range_start"),
            time_range_end=config.get("time_range_end"),
        )
        base["error_distribution"] = await get_error_distribution(
            db=db,
            group_by="error_type",
            benchmark=config.get("benchmark"),
            model_version=config.get("model_version"),
        )
        base["trends"] = await get_error_trends(
            db=db,
            benchmark=config.get("benchmark"),
            model_version=config.get("model_version"),
        )
        return base

    if report_kind == ReportType.comparison:
        version_a = config.get("version_a")
        version_b = config.get("version_b")
        if not version_a or not version_b:
            raise ValueError("comparison report requires version_a and version_b")

        base["comparison"] = await compare_versions(
            db=db,
            version_a=version_a,
            version_b=version_b,
            benchmark=config.get("benchmark"),
        )
        base["diff"] = await get_version_diff(
            db=db,
            version_a=version_a,
            version_b=version_b,
            benchmark=config.get("benchmark"),
        )
        base["radar"] = await get_radar_data(
            db=db,
            version_a=version_a,
            version_b=version_b,
            benchmark=config.get("benchmark"),
        )
        return base

    if report_kind == ReportType.cross_benchmark:
        base["matrix"] = await get_benchmark_matrix(db=db)
        base["weakness"] = await get_systematic_weaknesses(db=db)
        base["trends"] = await get_error_trends(db=db)
        return base

    # custom report: return flexible but with a useful default summary.
    base["summary"] = await get_analysis_summary(
        db=db,
        benchmark=config.get("benchmark"),
        model_version=config.get("model_version"),
        time_range_start=config.get("time_range_start"),
        time_range_end=config.get("time_range_end"),
    )
    return base
