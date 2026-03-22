from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.eval_record import EvalRecord
from app.db.models.eval_session import EvalSession


def _session_filters(version: str, benchmark: str | None) -> list[Any]:
    filters: list[Any] = [EvalSession.model_version == version]
    if benchmark:
        filters.append(EvalSession.benchmark == benchmark)
    return filters


async def _load_sessions(db: AsyncSession, version: str, benchmark: str | None) -> list[EvalSession]:
    stmt = select(EvalSession).where(*_session_filters(version, benchmark))
    return (await db.execute(stmt)).scalars().all()


def _aggregate_session_metrics(sessions: list[EvalSession]) -> tuple[int, float, float]:
    session_count = len(sessions)
    total_count = sum(int(s.total_count or 0) for s in sessions)
    total_errors = sum(int(s.error_count or 0) for s in sessions)
    weighted_accuracy = sum(float(s.accuracy or 0.0) * int(s.total_count or 0) for s in sessions)
    accuracy = (weighted_accuracy / total_count) if total_count else 0.0
    error_rate = (total_errors / total_count) if total_count else 0.0
    return session_count, round(accuracy, 4), round(error_rate, 4)


async def compare_versions(
    db: AsyncSession,
    version_a: str,
    version_b: str,
    benchmark: str | None,
) -> dict[str, Any]:
    sessions_a, sessions_b = await _load_sessions(db, version_a, benchmark), await _load_sessions(db, version_b, benchmark)

    session_count_a, accuracy_a, error_rate_a = _aggregate_session_metrics(sessions_a)
    session_count_b, accuracy_b, error_rate_b = _aggregate_session_metrics(sessions_b)

    return {
        "version_a": version_a,
        "version_b": version_b,
        "benchmark": benchmark,
        "sessions_a": session_count_a,
        "sessions_b": session_count_b,
        "accuracy_a": accuracy_a,
        "accuracy_b": accuracy_b,
        "accuracy_delta": round(accuracy_b - accuracy_a, 4),
        "error_rate_a": error_rate_a,
        "error_rate_b": error_rate_b,
        "error_rate_delta": round(error_rate_b - error_rate_a, 4),
    }


async def _load_version_records(
    db: AsyncSession,
    version: str,
    benchmark: str | None,
) -> list[EvalRecord]:
    stmt = (
        select(EvalRecord)
        .join(EvalSession, EvalSession.id == EvalRecord.session_id)
        .where(EvalSession.model_version == version)
    )
    if benchmark:
        stmt = stmt.where(EvalRecord.benchmark == benchmark)
    return (await db.execute(stmt)).scalars().all()


def _row_payload(record: EvalRecord, old_tag: str | None = None, new_tag: str | None = None) -> dict[str, Any]:
    return {
        "question_id": record.question_id,
        "benchmark": record.benchmark,
        "category": record.task_category,
        "old_tag": old_tag,
        "new_tag": new_tag,
    }


async def get_version_diff(
    db: AsyncSession,
    version_a: str,
    version_b: str,
    benchmark: str | None,
) -> dict[str, Any]:
    rows_a = await _load_version_records(db, version_a, benchmark)
    rows_b = await _load_version_records(db, version_b, benchmark)

    by_key_a = {(row.benchmark, row.question_id): row for row in rows_a}
    by_key_b = {(row.benchmark, row.question_id): row for row in rows_b}

    regressed: list[dict[str, Any]] = []
    improved: list[dict[str, Any]] = []
    new_errors: list[dict[str, Any]] = []
    fixed_errors: list[dict[str, Any]] = []

    for key in by_key_a.keys() & by_key_b.keys():
        old_row = by_key_a[key]
        new_row = by_key_b[key]
        old_correct = bool(old_row.is_correct)
        new_correct = bool(new_row.is_correct)
        if old_correct and not new_correct:
            regressed.append(_row_payload(new_row))
        elif not old_correct and new_correct:
            improved.append(_row_payload(new_row))

    for key in by_key_b.keys() - by_key_a.keys():
        row = by_key_b[key]
        if not bool(row.is_correct):
            new_errors.append(_row_payload(row))

    for key in by_key_a.keys() - by_key_b.keys():
        row = by_key_a[key]
        if not bool(row.is_correct):
            fixed_errors.append(_row_payload(row))

    return {
        "version_a": version_a,
        "version_b": version_b,
        "regressed": regressed,
        "improved": improved,
        "new_errors": new_errors,
        "fixed_errors": fixed_errors,
    }


async def get_radar_data(
    db: AsyncSession,
    version_a: str,
    version_b: str,
    benchmark: str | None,
) -> dict[str, Any]:
    rows_a = await _load_version_records(db, version_a, benchmark)
    rows_b = await _load_version_records(db, version_b, benchmark)

    def accumulate(records: list[EvalRecord]) -> dict[str, tuple[int, int]]:
        counter: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))
        for record in records:
            key = record.task_category or "(unknown)"
            total, correct = counter[key]
            counter[key] = (total + 1, correct + int(bool(record.is_correct)))
        return counter

    acc_a = accumulate(rows_a)
    acc_b = accumulate(rows_b)
    dimensions = sorted(set(acc_a.keys()) | set(acc_b.keys()))

    scores_a: list[float] = []
    scores_b: list[float] = []
    for dimension in dimensions:
        total_a, correct_a = acc_a.get(dimension, (0, 0))
        total_b, correct_b = acc_b.get(dimension, (0, 0))
        scores_a.append(round((correct_a / total_a), 4) if total_a else 0.0)
        scores_b.append(round((correct_b / total_b), 4) if total_b else 0.0)

    return {
        "version_a": version_a,
        "version_b": version_b,
        "dimensions": dimensions,
        "scores_a": scores_a,
        "scores_b": scores_b,
    }
