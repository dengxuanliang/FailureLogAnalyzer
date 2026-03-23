from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Sequence

from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import Delete

import pytest

from app.cli import seed_demo


class _FakeResult:
    def __init__(self, value: object | None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeTransaction:
    def __init__(self, session: "_FakeSession"):
        self._session = session

    async def __aenter__(self) -> "_FakeTransaction":
        self._session.in_transaction = True
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._session.in_transaction = False


class _FakeSession:
    def __init__(self):
        self.added_items: list[object] = []
        self.flush_count = 0
        self.begin_calls = 0
        self.executed_statements: list[object] = []
        self.in_transaction = False

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def begin(self):
        self.begin_calls += 1
        return _FakeTransaction(self)

    async def execute(self, stmt):
        self.executed_statements.append(stmt)
        return _FakeResult(None)

    def add_all(self, items: Sequence[object]):
        self.added_items.extend(items)

    def add(self, item: object):
        self.added_items.append(item)

    async def flush(self) -> None:
        self.flush_count += 1


def _fake_get_async_session(session: _FakeSession):
    @asynccontextmanager
    async def _cm():
        yield session

    return _cm


@pytest.mark.asyncio
async def test_demo_query_targets_demo_model_and_dataset():
    stmt = seed_demo._demo_session_exists_stmt()
    compiled = stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "demo-model" in sql
    assert "demo-set" in sql


@pytest.mark.asyncio
async def test_seed_skips_when_demo_data_exists(monkeypatch, capsys):
    session = _FakeSession()
    monkeypatch.setattr(seed_demo, "get_async_session", _fake_get_async_session(session))
    async def _demo_exists(_db):
        return object()
    monkeypatch.setattr(seed_demo, "_demo_session_exists", _demo_exists)

    await seed_demo._seed(force=False)

    captured = capsys.readouterr()
    assert "already exists" in captured.out
    assert session.begin_calls == 1
    assert session.added_items == []
    assert session.executed_statements == []
    assert session.flush_count == 0


@pytest.mark.asyncio
async def test_seed_force_purges_demo_data(monkeypatch):
    session = _FakeSession()
    monkeypatch.setattr(seed_demo, "get_async_session", _fake_get_async_session(session))
    async def _demo_exists(_db):
        return object()
    monkeypatch.setattr(seed_demo, "_demo_session_exists", _demo_exists)

    await seed_demo._seed(force=True)

    assert session.begin_calls == 1
    tables = {stmt.table.name for stmt in session.executed_statements if isinstance(stmt, Delete)}
    assert {"eval_sessions", "reports"}.issubset(tables)
    types = {type(item).__name__ for item in session.added_items}
    assert "EvalSession" in types
    assert "EvalRecord" in types
    assert "AnalysisResult" in types
    assert "ErrorTag" in types
    assert "Report" in types
    assert session.flush_count == 3
