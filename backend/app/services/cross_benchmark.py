from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.error_tag import ErrorTag
from app.db.models.eval_record import EvalRecord
from app.db.models.eval_session import EvalSession


async def get_benchmark_matrix(db: AsyncSession) -> dict[str, Any]:
    stmt = select(EvalSession.model_version, EvalSession.benchmark, EvalSession.accuracy)
    rows = (await db.execute(stmt)).all()

    models = sorted({row.model_version for row in rows if row.model_version})
    benchmarks = sorted({row.benchmark for row in rows if row.benchmark})

    score_map: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        if row.model_version and row.benchmark and row.accuracy is not None:
            score_map[(row.model_version, row.benchmark)].append(float(row.accuracy))

    matrix: list[list[float]] = []
    for model in models:
        row_values: list[float] = []
        for benchmark in benchmarks:
            values = score_map.get((model, benchmark), [])
            row_values.append(round(sum(values) / len(values), 4) if values else 0.0)
        matrix.append(row_values)

    return {"models": models, "benchmarks": benchmarks, "matrix": matrix}


async def get_systematic_weaknesses(db: AsyncSession, min_occurrences: int = 2) -> dict[str, Any]:
    # Fetch tag + benchmark and aggregate in Python for portability.
    stmt = (
        select(ErrorTag.tag_path, EvalRecord.benchmark)
        .join(EvalRecord, EvalRecord.id == ErrorTag.record_id)
    )
    rows = (await db.execute(stmt)).all()

    by_tag_benchmark: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        l1_tag = (row.tag_path or "(unknown)").split(".")[0]
        by_tag_benchmark[l1_tag][row.benchmark or "(unknown)"] += 1

    weaknesses: list[dict[str, Any]] = []
    for tag, benchmark_counts in by_tag_benchmark.items():
        total = sum(benchmark_counts.values())
        if total < min_occurrences:
            continue
        avg_error_rate = total / max(len(benchmark_counts), 1)
        weaknesses.append(
            {
                "tag": tag,
                "affected_benchmarks": sorted(benchmark_counts.keys()),
                "avg_error_rate": round(avg_error_rate, 4),
            }
        )

    weaknesses.sort(key=lambda item: item["avg_error_rate"], reverse=True)
    return {"weaknesses": weaknesses}


async def get_error_trends(
    db: AsyncSession,
    benchmark: str | None = None,
    model_version: str | None = None,
) -> dict[str, Any]:
    filters = []
    if benchmark:
        filters.append(EvalSession.benchmark == benchmark)
    if model_version:
        filters.append(EvalSession.model_version == model_version)

    day_expr = func.date(EvalSession.created_at)
    stmt = (
        select(
            day_expr.label("day"),
            EvalSession.benchmark,
            EvalSession.model_version,
            func.sum(EvalSession.error_count).label("errors"),
            func.sum(EvalSession.total_count).label("totals"),
        )
        .where(*filters)
        .group_by(day_expr, EvalSession.benchmark, EvalSession.model_version)
        .order_by(day_expr.asc())
    )

    rows = (await db.execute(stmt)).all()

    data_points: list[dict[str, Any]] = []
    for row in rows:
        totals = int(row.totals or 0)
        errors = int(row.errors or 0)
        error_rate = (errors / totals) if totals else 0.0
        day_val = row.day
        if isinstance(day_val, date):
            day_text = day_val.isoformat()
        else:
            day_text = str(day_val)
        data_points.append(
            {
                "date": day_text,
                "error_rate": round(error_rate, 4),
                "benchmark": row.benchmark,
                "model_version": row.model_version,
            }
        )

    return {"data_points": data_points}
