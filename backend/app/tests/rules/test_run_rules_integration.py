"""Integration-style test for run_rules batch write behavior."""
from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import pytest


class _FakeScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return list(self._rows)


class _FakeExecuteResult:
    def __init__(self, rows: list[object] | None = None, scalar_value: object | None = None) -> None:
        self._rows = rows or []
        self._scalar_value = scalar_value

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self._rows)

    def scalar(self) -> object | None:
        return self._scalar_value


@dataclass
class _FakeAsyncSession:
    records: list[object]
    session_avg_length: float | None
    custom_rules: list[object] = field(default_factory=list)
    added: list[object] = field(default_factory=list)
    commits: int = 0
    _record_query_calls: int = 0

    async def execute(self, stmt):  # noqa: ANN001
        from app.db.models.analysis_rule import AnalysisRule
        from app.db.models.eval_record import EvalRecord

        if "avg(" in str(stmt).lower():
            return _FakeExecuteResult(scalar_value=self.session_avg_length)

        entity = stmt.column_descriptions[0].get("entity")
        if entity is AnalysisRule:
            return _FakeExecuteResult(rows=self.custom_rules)
        if entity is EvalRecord:
            self._record_query_calls += 1
            if self._record_query_calls == 1:
                return _FakeExecuteResult(rows=self.records)
            return _FakeExecuteResult(rows=[])
        return _FakeExecuteResult(rows=[])

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                setattr(obj, "id", uuid.uuid4())

    async def commit(self) -> None:
        self.commits += 1


@pytest.mark.integration
def test_run_rules_writes_analysis_result_and_tags(monkeypatch):
    """Full round-trip over mocked async DB session and real rule evaluation."""
    from app.tasks import analysis as analysis_task
    from app.db.models.eval_record import EvalRecord
    from app.db.models.analysis_result import AnalysisResult
    from app.db.models.error_tag import ErrorTag

    session_id = uuid.uuid4()
    record = EvalRecord(
        session_id=session_id,
        benchmark="test",
        model_answer="",
        expected_answer="42",
        question="What is 6×7?",
        is_correct=False,
        score=0.0,
        metadata_={},
        raw_json={},
    )

    fake_db = _FakeAsyncSession(records=[record], session_avg_length=10.0)

    @asynccontextmanager
    async def _fake_get_async_session():
        yield fake_db

    monkeypatch.setattr(analysis_task, "get_async_session", _fake_get_async_session)

    summary = asyncio.run(
        analysis_task._run_rules_for_session_async(
            session_id=str(session_id),
            rule_ids=None,
            batch_size=100,
        )
    )

    assert summary["session_id"] == str(session_id)
    assert summary["total_processed"] == 1
    assert summary["total_tagged"] >= 1

    analysis_results = [obj for obj in fake_db.added if isinstance(obj, AnalysisResult)]
    error_tags = [obj for obj in fake_db.added if isinstance(obj, ErrorTag)]

    assert len(analysis_results) == 1
    assert any(tag.tag_path == "格式与规范错误.空回答/拒绝回答" for tag in error_tags)
    assert fake_db.commits == 1
