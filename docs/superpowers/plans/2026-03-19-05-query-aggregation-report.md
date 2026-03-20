# Query & Aggregation Layer + Report Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Query & Aggregation Layer and Report Agent — all read-oriented REST APIs that power the Dashboard (analysis summary, error distribution, error record browsing, version comparison, cross-benchmark matrix, trend analysis) plus a Celery-backed report generation pipeline that aggregates data into shareable report snapshots.

**Architecture:** Pure query endpoints live in dedicated FastAPI routers grouped by domain (analysis, compare, cross-benchmark, trends). Each router calls a thin service module containing the SQLAlchemy queries, keeping routers free of query logic. The Report Agent is a Celery task (`tasks.report.generate_report`) that runs aggregation queries, builds a structured JSON report, writes it to a `reports` table, and publishes a completion event to Redis for WebSocket relay. All aggregation queries hit the existing `eval_sessions`, `eval_records`, `analysis_results`, and `error_tags` tables — no new domain tables except `reports`.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 (async), Celery 5 + Redis, pytest + pytest-asyncio, factory-boy, httpx (AsyncClient for tests)

---

## Prerequisites (Plans 1–4 must be complete)

Plan 1 provides:
- `/backend/app/db/` — SQLAlchemy engine, `Base`, session factories
- `/backend/app/db/session.py` — `get_db()` async dep + `get_db_session()` sync context manager
- `/backend/app/models/` — all ORM models (`EvalSession`, `EvalRecord`, `AnalysisResult`, `ErrorTag`, `User`)
- `/backend/app/core/config.py` — `Settings`
- `/backend/app/celery_app.py` — Celery application instance
- `/backend/app/api/v1/deps.py` — `get_db`, `require_role`
- `/backend/app/main.py` — FastAPI app with router registration

Plan 2 provides:
- `/backend/app/models/eval_session.py` — `EvalSession` ORM model
- `/backend/app/models/eval_record.py` — `EvalRecord` ORM model
- Session/record data in DB for querying

Plan 3 provides:
- `/backend/app/models/error_tag.py` — `ErrorTag` ORM model
- `/backend/app/models/analysis_result.py` — `AnalysisResult` ORM model
- `/backend/app/rules/taxonomy.py` — `TaxonomyTree`

Plan 4 provides:
- LLM analysis results in `analysis_results` and `error_tags` tables
- `/backend/app/llm/cost_calculator.py` — cost data

---

## File Structure After This Plan

```
backend/app/
  models/
    report.py               # Report ORM model (NEW)
  schemas/
    analysis_query.py        # Pydantic schemas for analysis query responses
    compare.py               # Pydantic schemas for version comparison responses
    cross_benchmark.py       # Pydantic schemas for cross-benchmark responses
    report.py                # Pydantic schemas for report CRUD
  services/
    __init__.py
    analysis_query.py        # Analysis summary / distribution / record list queries
    compare.py               # Version comparison queries
    cross_benchmark.py       # Cross-benchmark matrix / weakness queries
    report_builder.py        # Report generation logic (called by Celery task)
  tasks/
    report.py                # Celery task: generate_report
  api/v1/routers/
    analysis.py              # GET /analysis/summary, /error-distribution, /records, /records/{id}/detail
    compare.py               # GET /compare/versions, /compare/diff, /compare/radar
    cross_benchmark.py       # GET /cross-benchmark/matrix, /cross-benchmark/weakness
    trends.py                # GET /trends
    reports.py               # POST /reports/generate, GET /reports, GET /reports/{id}

tests/
  services/
    test_analysis_query.py
    test_compare.py
    test_cross_benchmark.py
    test_report_builder.py
  tasks/
    test_generate_report.py
  api/
    test_analysis_api.py
    test_compare_api.py
    test_cross_benchmark_api.py
    test_trends_api.py
    test_reports_api.py
```

---

## Phase 1 — Report ORM Model + Migration

### Task 1.1 — Create Report model

**Files:**
- Create: `backend/app/models/report.py`

- [ ] **Step 1: Write `app/models/report.py`**

```python
# backend/app/models/report.py
"""Report ORM model — stores generated analysis report snapshots."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    report_type = Column(
        SAEnum("summary", "comparison", "cross_benchmark", "custom", name="report_type_enum"),
        nullable=False,
        default="summary",
    )
    # Scope filters used to generate the report
    session_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    benchmark = Column(String(255), nullable=True)
    model_version = Column(String(255), nullable=True)
    time_range_start = Column(DateTime, nullable=True)
    time_range_end = Column(DateTime, nullable=True)
    # Report content
    content = Column(JSONB, nullable=False, default=dict)
    # Metadata
    status = Column(
        SAEnum("pending", "generating", "done", "failed", name="report_status_enum"),
        nullable=False,
        default="pending",
    )
    error_message = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
```

- [ ] **Step 2: Generate Alembic migration**

```bash
cd backend && alembic revision --autogenerate -m "add reports table"
```

- [ ] **Step 3: Apply migration**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/report.py backend/alembic/versions/
git commit -m "feat(report): add Report ORM model and migration"
```

---

## Phase 2 — Analysis Query Service + Schemas

### Task 2.1 — Write failing test for analysis query service

**Files:**
- Create: `backend/tests/services/test_analysis_query.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/analysis_query.py`
- Create: `backend/app/schemas/analysis_query.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/services/test_analysis_query.py
"""Unit tests for analysis query service — uses in-memory DB fixtures."""
import pytest
import uuid
from datetime import datetime
from unittest.mock import MagicMock
from app.services.analysis_query import (
    get_analysis_summary,
    get_error_distribution,
    get_error_records_page,
    get_record_detail,
)


def _make_session(**kwargs):
    defaults = dict(
        id=uuid.uuid4(), model="test-model", model_version="v1",
        benchmark="mmlu", dataset_name="mmlu-test",
        total_count=100, error_count=30, accuracy=0.7,
        config={}, tags=[], created_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _make_tag(**kwargs):
    defaults = dict(
        id=uuid.uuid4(), record_id=uuid.uuid4(),
        analysis_result_id=uuid.uuid4(),
        tag_path="推理性错误.逻辑推理错误.前提正确但推理链断裂",
        tag_level=3, source="rule", confidence=0.9,
        created_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


# --- AnalysisSummary --------------------------------------------------------

def test_analysis_summary_returns_correct_shape(db_session):
    """
    Requires db_session fixture with seeded eval_sessions and error_tags.
    See conftest.py for fixture details.
    """
    result = get_analysis_summary(
        db=db_session,
        benchmark=None,
        model_version=None,
        time_range_start=None,
        time_range_end=None,
    )
    assert "total_sessions" in result
    assert "total_records" in result
    assert "total_errors" in result
    assert "accuracy" in result
    assert "llm_analysed_count" in result
    assert "llm_total_cost" in result


# --- ErrorDistribution ------------------------------------------------------

def test_error_distribution_by_error_type(db_session):
    result = get_error_distribution(
        db=db_session,
        group_by="error_type",
        benchmark=None,
        model_version=None,
    )
    assert isinstance(result, list)
    # Each item: {"label": str, "count": int, "percentage": float}
    if len(result) > 0:
        item = result[0]
        assert "label" in item
        assert "count" in item
        assert "percentage" in item


def test_error_distribution_by_category(db_session):
    result = get_error_distribution(
        db=db_session,
        group_by="category",
        benchmark=None,
        model_version=None,
    )
    assert isinstance(result, list)


def test_error_distribution_by_severity(db_session):
    result = get_error_distribution(
        db=db_session,
        group_by="severity",
        benchmark=None,
        model_version=None,
    )
    assert isinstance(result, list)


# --- Paginated error records ------------------------------------------------

def test_error_records_page_returns_paginated(db_session):
    result = get_error_records_page(
        db=db_session,
        error_type=None,
        benchmark=None,
        model_version=None,
        page=1,
        size=20,
    )
    assert "items" in result
    assert "total" in result
    assert "page" in result
    assert "size" in result


# --- Record detail ----------------------------------------------------------

def test_record_detail_returns_full_info(db_session, seeded_record_id):
    result = get_record_detail(db=db_session, record_id=seeded_record_id)
    assert result is not None
    assert "record" in result
    assert "analysis_results" in result
    assert "error_tags" in result


def test_record_detail_not_found(db_session):
    result = get_record_detail(db=db_session, record_id=uuid.uuid4())
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_analysis_query.py -x`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services'`

### Task 2.2 — Write analysis query schemas

- [ ] **Step 3: Write `app/schemas/analysis_query.py`**

```python
# backend/app/schemas/analysis_query.py
"""Pydantic schemas for analysis query API responses."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class AnalysisSummary(BaseModel):
    total_sessions: int
    total_records: int
    total_errors: int
    accuracy: float
    llm_analysed_count: int
    llm_total_cost: float


class DistributionItem(BaseModel):
    label: str
    count: int
    percentage: float


class ErrorRecordBrief(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    benchmark: str
    task_category: Optional[str]
    question_id: Optional[str]
    question: str
    is_correct: bool
    score: Optional[float]
    error_tags: list[str] = Field(default_factory=list)
    has_llm_analysis: bool = False

    model_config = {"from_attributes": True}


class PaginatedRecords(BaseModel):
    items: list[ErrorRecordBrief]
    total: int
    page: int
    size: int


class AnalysisResultDetail(BaseModel):
    id: uuid.UUID
    analysis_type: str
    error_types: list[str]
    root_cause: Optional[str]
    severity: Optional[str]
    confidence: Optional[float]
    evidence: Optional[str]
    suggestion: Optional[str]
    llm_model: Optional[str]
    llm_cost: Optional[float]
    unmatched_tags: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class RecordDetail(BaseModel):
    record: dict[str, Any]
    analysis_results: list[AnalysisResultDetail]
    error_tags: list[dict[str, Any]]
```

### Task 2.3 — Implement analysis query service

- [ ] **Step 4: Create `app/services/__init__.py`**

```bash
mkdir -p backend/app/services backend/tests/services
touch backend/app/services/__init__.py backend/tests/services/__init__.py
```

- [ ] **Step 5: Write `app/services/analysis_query.py`**

```python
# backend/app/services/analysis_query.py
"""Query logic for analysis summary, error distribution, and record browsing."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, and_, case

from app.models.eval_session import EvalSession
from app.models.eval_record import EvalRecord
from app.models.analysis_result import AnalysisResult
from app.models.error_tag import ErrorTag


def get_analysis_summary(
    db: Session,
    benchmark: Optional[str],
    model_version: Optional[str],
    time_range_start: Optional[datetime],
    time_range_end: Optional[datetime],
) -> dict[str, Any]:
    """Return overview metrics: total sessions/records/errors, accuracy, LLM stats."""
    session_q = db.query(EvalSession)
    if benchmark:
        session_q = session_q.filter(EvalSession.benchmark == benchmark)
    if model_version:
        session_q = session_q.filter(EvalSession.model_version == model_version)
    if time_range_start:
        session_q = session_q.filter(EvalSession.created_at >= time_range_start)
    if time_range_end:
        session_q = session_q.filter(EvalSession.created_at <= time_range_end)

    sessions = session_q.all()
    session_ids = [s.id for s in sessions]

    total_sessions = len(sessions)
    total_records = sum(s.total_count or 0 for s in sessions)
    total_errors = sum(s.error_count or 0 for s in sessions)
    accuracy = (
        sum((s.accuracy or 0) * (s.total_count or 0) for s in sessions) / total_records
        if total_records > 0
        else 0.0
    )

    # LLM analysis stats
    if session_ids:
        llm_stats = (
            db.query(
                sqlfunc.count(AnalysisResult.id).label("cnt"),
                sqlfunc.coalesce(sqlfunc.sum(AnalysisResult.llm_cost), 0).label("cost"),
            )
            .join(EvalRecord, EvalRecord.id == AnalysisResult.record_id)
            .filter(
                EvalRecord.session_id.in_(session_ids),
                AnalysisResult.analysis_type == "llm",
            )
            .one()
        )
        llm_count = int(llm_stats.cnt)
        llm_cost = float(llm_stats.cost)
    else:
        llm_count = 0
        llm_cost = 0.0

    return {
        "total_sessions": total_sessions,
        "total_records": total_records,
        "total_errors": total_errors,
        "accuracy": round(accuracy, 4),
        "llm_analysed_count": llm_count,
        "llm_total_cost": round(llm_cost, 6),
    }


def get_error_distribution(
    db: Session,
    group_by: str,
    benchmark: Optional[str],
    model_version: Optional[str],
) -> list[dict[str, Any]]:
    """
    Return error distribution grouped by error_type (L1 tag), category, or severity.

    group_by: 'error_type' | 'category' | 'severity'
    """
    base_q = db.query(ErrorTag).join(
        EvalRecord, EvalRecord.id == ErrorTag.record_id
    )
    if benchmark:
        base_q = base_q.filter(EvalRecord.benchmark == benchmark)
    if model_version:
        base_q = base_q.join(
            EvalSession, EvalSession.id == EvalRecord.session_id
        ).filter(EvalSession.model_version == model_version)

    if group_by == "error_type":
        # Group by L1 tag (first segment of tag_path)
        l1_expr = sqlfunc.split_part(ErrorTag.tag_path, ".", 1)
        rows = (
            base_q.with_entities(
                l1_expr.label("label"),
                sqlfunc.count(ErrorTag.id).label("cnt"),
            )
            .group_by(l1_expr)
            .order_by(sqlfunc.count(ErrorTag.id).desc())
            .all()
        )
    elif group_by == "category":
        rows = (
            base_q.with_entities(
                EvalRecord.task_category.label("label"),
                sqlfunc.count(ErrorTag.id).label("cnt"),
            )
            .group_by(EvalRecord.task_category)
            .order_by(sqlfunc.count(ErrorTag.id).desc())
            .all()
        )
    elif group_by == "severity":
        # Join to analysis_results for severity
        rows = (
            base_q.join(
                AnalysisResult, AnalysisResult.id == ErrorTag.analysis_result_id
            )
            .with_entities(
                AnalysisResult.severity.label("label"),
                sqlfunc.count(ErrorTag.id).label("cnt"),
            )
            .group_by(AnalysisResult.severity)
            .order_by(sqlfunc.count(ErrorTag.id).desc())
            .all()
        )
    else:
        raise ValueError(f"Invalid group_by: {group_by!r}. Must be error_type|category|severity")

    total = sum(r.cnt for r in rows) if rows else 0
    return [
        {
            "label": r.label or "(unknown)",
            "count": r.cnt,
            "percentage": round(r.cnt / total * 100, 2) if total > 0 else 0.0,
        }
        for r in rows
    ]


def get_error_records_page(
    db: Session,
    error_type: Optional[str],
    benchmark: Optional[str],
    model_version: Optional[str],
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """Return paginated error records with tag summaries."""
    q = db.query(EvalRecord).filter(EvalRecord.is_correct == False)  # noqa: E712

    if benchmark:
        q = q.filter(EvalRecord.benchmark == benchmark)
    if model_version:
        q = q.join(
            EvalSession, EvalSession.id == EvalRecord.session_id
        ).filter(EvalSession.model_version == model_version)
    if error_type:
        # Filter to records that have a matching error tag
        q = q.filter(
            EvalRecord.id.in_(
                db.query(ErrorTag.record_id)
                .filter(ErrorTag.tag_path.like(f"{error_type}%"))
                .subquery()
            )
        )

    total = q.count()
    offset = (page - 1) * size
    records = q.order_by(EvalRecord.created_at.desc()).offset(offset).limit(size).all()

    items = []
    for rec in records:
        tags = (
            db.query(ErrorTag.tag_path)
            .filter(ErrorTag.record_id == rec.id)
            .all()
        )
        has_llm = (
            db.query(AnalysisResult)
            .filter(
                AnalysisResult.record_id == rec.id,
                AnalysisResult.analysis_type == "llm",
            )
            .first()
        ) is not None

        items.append({
            "id": rec.id,
            "session_id": rec.session_id,
            "benchmark": rec.benchmark,
            "task_category": getattr(rec, "task_category", None),
            "question_id": getattr(rec, "question_id", None),
            "question": rec.question or "",
            "is_correct": rec.is_correct,
            "score": getattr(rec, "score", None),
            "error_tags": [t[0] for t in tags],
            "has_llm_analysis": has_llm,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


def get_record_detail(
    db: Session,
    record_id: uuid.UUID,
) -> Optional[dict[str, Any]]:
    """Return full detail for a single record including all analysis and tags."""
    rec = db.get(EvalRecord, record_id)
    if rec is None:
        return None

    analysis_rows = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.record_id == record_id)
        .order_by(AnalysisResult.created_at)
        .all()
    )
    tag_rows = (
        db.query(ErrorTag)
        .filter(ErrorTag.record_id == record_id)
        .order_by(ErrorTag.created_at)
        .all()
    )

    return {
        "record": {
            "id": rec.id,
            "session_id": rec.session_id,
            "benchmark": rec.benchmark,
            "task_category": getattr(rec, "task_category", None),
            "question_id": getattr(rec, "question_id", None),
            "question": rec.question or "",
            "expected_answer": getattr(rec, "expected_answer", None),
            "model_answer": getattr(rec, "model_answer", None),
            "is_correct": rec.is_correct,
            "score": getattr(rec, "score", None),
            "extracted_code": getattr(rec, "extracted_code", None),
            "metadata": getattr(rec, "metadata", {}),
        },
        "analysis_results": [
            {
                "id": ar.id,
                "analysis_type": ar.analysis_type,
                "error_types": ar.error_types or [],
                "root_cause": getattr(ar, "root_cause", None),
                "severity": getattr(ar, "severity", None),
                "confidence": getattr(ar, "confidence", None),
                "evidence": getattr(ar, "evidence", None),
                "suggestion": getattr(ar, "suggestion", None),
                "llm_model": getattr(ar, "llm_model", None),
                "llm_cost": getattr(ar, "llm_cost", None),
                "unmatched_tags": getattr(ar, "unmatched_tags", []) or [],
                "created_at": ar.created_at,
            }
            for ar in analysis_rows
        ],
        "error_tags": [
            {
                "id": t.id,
                "tag_path": t.tag_path,
                "tag_level": t.tag_level,
                "source": t.source,
                "confidence": t.confidence,
            }
            for t in tag_rows
        ],
    }
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/services/test_analysis_query.py -x -v`
Expected: 7 passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/ backend/app/schemas/analysis_query.py backend/tests/services/
git commit -m "feat(query): add analysis query service with summary, distribution, pagination, and detail"
```

---

## Phase 3 — Version Comparison Service

### Task 3.1 — Write failing test for comparison service

**Files:**
- Create: `backend/tests/services/test_compare.py`
- Create: `backend/app/services/compare.py`
- Create: `backend/app/schemas/compare.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/services/test_compare.py
"""Unit tests for version comparison service."""
import pytest
import uuid
from app.services.compare import (
    compare_versions,
    get_version_diff,
    get_radar_data,
)


def test_compare_versions_returns_metrics(db_session):
    result = compare_versions(
        db=db_session,
        version_a="v1",
        version_b="v2",
        benchmark=None,
    )
    assert "version_a" in result
    assert "version_b" in result
    assert "metrics_a" in result
    assert "metrics_b" in result
    # Each metrics block: total, errors, accuracy
    for key in ("total", "errors", "accuracy"):
        assert key in result["metrics_a"]
        assert key in result["metrics_b"]


def test_version_diff_identifies_changes(db_session):
    result = get_version_diff(
        db=db_session,
        version_a="v1",
        version_b="v2",
        benchmark=None,
    )
    assert "regressed" in result  # questions correct in A but wrong in B
    assert "improved" in result   # questions wrong in A but correct in B
    assert "new_errors" in result  # error types in B not in A
    assert isinstance(result["regressed"], list)
    assert isinstance(result["improved"], list)


def test_radar_data_returns_dimensions(db_session):
    result = get_radar_data(
        db=db_session,
        version_a="v1",
        version_b="v2",
        benchmark=None,
    )
    assert "dimensions" in result
    assert "scores_a" in result
    assert "scores_b" in result
    assert isinstance(result["dimensions"], list)
    # scores lists should match dimensions length
    assert len(result["scores_a"]) == len(result["dimensions"])
    assert len(result["scores_b"]) == len(result["dimensions"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_compare.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 3.2 — Write comparison schemas

- [ ] **Step 3: Write `app/schemas/compare.py`**

```python
# backend/app/schemas/compare.py
"""Pydantic schemas for version comparison API responses."""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class VersionMetrics(BaseModel):
    total: int
    errors: int
    accuracy: float
    error_type_distribution: dict[str, int] = Field(default_factory=dict)


class VersionComparison(BaseModel):
    version_a: str
    version_b: str
    benchmark: Optional[str]
    metrics_a: VersionMetrics
    metrics_b: VersionMetrics


class DiffItem(BaseModel):
    question_id: str
    benchmark: str
    task_category: Optional[str]
    question: str


class VersionDiff(BaseModel):
    regressed: list[DiffItem]       # correct in A, wrong in B
    improved: list[DiffItem]        # wrong in A, correct in B
    new_errors: list[str]           # error types in B not in A
    resolved_errors: list[str]      # error types in A not in B


class RadarData(BaseModel):
    dimensions: list[str]           # task_category names
    scores_a: list[float]           # accuracy per dimension for version A
    scores_b: list[float]           # accuracy per dimension for version B
```

### Task 3.3 — Implement comparison service

- [ ] **Step 4: Write `app/services/compare.py`**

```python
# backend/app/services/compare.py
"""Version comparison query logic."""
from __future__ import annotations
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.models.eval_session import EvalSession
from app.models.eval_record import EvalRecord
from app.models.error_tag import ErrorTag


def _get_records_for_version(
    db: Session,
    version: str,
    benchmark: Optional[str],
):
    """Return all eval_records for a model_version, optionally filtered by benchmark."""
    q = (
        db.query(EvalRecord)
        .join(EvalSession, EvalSession.id == EvalRecord.session_id)
        .filter(EvalSession.model_version == version)
    )
    if benchmark:
        q = q.filter(EvalRecord.benchmark == benchmark)
    return q.all()


def _version_metrics(records: list) -> dict[str, Any]:
    total = len(records)
    errors = sum(1 for r in records if not r.is_correct)
    accuracy = (total - errors) / total if total > 0 else 0.0
    return {"total": total, "errors": errors, "accuracy": round(accuracy, 4)}


def compare_versions(
    db: Session,
    version_a: str,
    version_b: str,
    benchmark: Optional[str],
) -> dict[str, Any]:
    """Compare aggregate metrics between two model versions."""
    recs_a = _get_records_for_version(db, version_a, benchmark)
    recs_b = _get_records_for_version(db, version_b, benchmark)

    return {
        "version_a": version_a,
        "version_b": version_b,
        "benchmark": benchmark,
        "metrics_a": _version_metrics(recs_a),
        "metrics_b": _version_metrics(recs_b),
    }


def get_version_diff(
    db: Session,
    version_a: str,
    version_b: str,
    benchmark: Optional[str],
) -> dict[str, Any]:
    """Find regressed, improved questions and new/resolved error types between versions."""
    recs_a = _get_records_for_version(db, version_a, benchmark)
    recs_b = _get_records_for_version(db, version_b, benchmark)

    # Build question_id -> is_correct maps
    map_a = {r.question_id: r for r in recs_a if r.question_id}
    map_b = {r.question_id: r for r in recs_b if r.question_id}

    common_ids = set(map_a.keys()) & set(map_b.keys())

    regressed = []
    improved = []
    for qid in common_ids:
        ra, rb = map_a[qid], map_b[qid]
        if ra.is_correct and not rb.is_correct:
            regressed.append({
                "question_id": qid,
                "benchmark": rb.benchmark,
                "task_category": getattr(rb, "task_category", None),
                "question": rb.question or "",
            })
        elif not ra.is_correct and rb.is_correct:
            improved.append({
                "question_id": qid,
                "benchmark": ra.benchmark,
                "task_category": getattr(ra, "task_category", None),
                "question": ra.question or "",
            })

    # Error type comparison
    def _get_error_types(records):
        ids = [r.id for r in records if not r.is_correct]
        if not ids:
            return set()
        tags = db.query(ErrorTag.tag_path).filter(ErrorTag.record_id.in_(ids)).all()
        return {t[0] for t in tags}

    types_a = _get_error_types(recs_a)
    types_b = _get_error_types(recs_b)

    return {
        "regressed": regressed,
        "improved": improved,
        "new_errors": sorted(types_b - types_a),
        "resolved_errors": sorted(types_a - types_b),
    }


def get_radar_data(
    db: Session,
    version_a: str,
    version_b: str,
    benchmark: Optional[str],
) -> dict[str, Any]:
    """Build radar chart data: accuracy per task_category for two versions."""
    recs_a = _get_records_for_version(db, version_a, benchmark)
    recs_b = _get_records_for_version(db, version_b, benchmark)

    # Collect all categories
    all_categories = sorted({
        getattr(r, "task_category", None) or "(unknown)"
        for r in recs_a + recs_b
    })

    def _accuracy_by_category(records):
        by_cat: dict[str, list[bool]] = {}
        for r in records:
            cat = getattr(r, "task_category", None) or "(unknown)"
            by_cat.setdefault(cat, []).append(r.is_correct)
        return {
            cat: sum(vals) / len(vals) if vals else 0.0
            for cat, vals in by_cat.items()
        }

    acc_a = _accuracy_by_category(recs_a)
    acc_b = _accuracy_by_category(recs_b)

    return {
        "dimensions": all_categories,
        "scores_a": [round(acc_a.get(c, 0.0), 4) for c in all_categories],
        "scores_b": [round(acc_b.get(c, 0.0), 4) for c in all_categories],
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/services/test_compare.py -x -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/compare.py backend/app/schemas/compare.py backend/tests/services/test_compare.py
git commit -m "feat(query): add version comparison service with diff and radar chart data"
```

---

## Phase 4 — Cross-Benchmark Service

### Task 4.1 — Write failing test for cross-benchmark service

**Files:**
- Create: `backend/tests/services/test_cross_benchmark.py`
- Create: `backend/app/services/cross_benchmark.py`
- Create: `backend/app/schemas/cross_benchmark.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/services/test_cross_benchmark.py
"""Unit tests for cross-benchmark analysis service."""
import pytest
from app.services.cross_benchmark import (
    get_benchmark_matrix,
    get_systematic_weaknesses,
    get_error_trends,
)


def test_matrix_returns_grid(db_session):
    result = get_benchmark_matrix(db=db_session)
    assert "models" in result           # list of model_version strings
    assert "benchmarks" in result       # list of benchmark strings
    assert "matrix" in result           # list[list[float]] — error rates
    if result["models"] and result["benchmarks"]:
        assert len(result["matrix"]) == len(result["models"])
        assert len(result["matrix"][0]) == len(result["benchmarks"])


def test_weaknesses_returns_patterns(db_session):
    result = get_systematic_weaknesses(db=db_session)
    assert "weaknesses" in result
    assert isinstance(result["weaknesses"], list)
    # Each weakness: {"error_type": str, "benchmarks": list[str], "frequency": int}


def test_error_trends_returns_time_series(db_session):
    result = get_error_trends(
        db=db_session,
        benchmark=None,
        model_version=None,
    )
    assert "data_points" in result
    assert isinstance(result["data_points"], list)
    # Each: {"period": str, "error_rate": float, "total": int, "errors": int}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_cross_benchmark.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 4.2 — Write cross-benchmark schemas

- [ ] **Step 3: Write `app/schemas/cross_benchmark.py`**

```python
# backend/app/schemas/cross_benchmark.py
"""Pydantic schemas for cross-benchmark API responses."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class BenchmarkMatrix(BaseModel):
    models: list[str]               # model_version labels (rows)
    benchmarks: list[str]           # benchmark labels (columns)
    matrix: list[list[float]]       # error_rate[model_idx][benchmark_idx]


class Weakness(BaseModel):
    error_type: str
    benchmarks: list[str]
    frequency: int


class SystematicWeaknesses(BaseModel):
    weaknesses: list[Weakness]


class TrendPoint(BaseModel):
    period: str                     # YYYY-MM or model_version
    error_rate: float
    total: int
    errors: int


class ErrorTrends(BaseModel):
    data_points: list[TrendPoint]
```

### Task 4.3 — Implement cross-benchmark service

- [ ] **Step 4: Write `app/services/cross_benchmark.py`**

```python
# backend/app/services/cross_benchmark.py
"""Cross-benchmark analysis and trend queries."""
from __future__ import annotations
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc, extract

from app.models.eval_session import EvalSession
from app.models.eval_record import EvalRecord
from app.models.error_tag import ErrorTag


def get_benchmark_matrix(db: Session) -> dict[str, Any]:
    """
    Return model_version x benchmark error rate matrix.

    Rows = distinct model_versions, Columns = distinct benchmarks.
    Cell value = error_rate (errors / total).
    """
    rows = (
        db.query(
            EvalSession.model_version,
            EvalSession.benchmark,
            sqlfunc.sum(EvalSession.error_count).label("errors"),
            sqlfunc.sum(EvalSession.total_count).label("total"),
        )
        .group_by(EvalSession.model_version, EvalSession.benchmark)
        .order_by(EvalSession.model_version, EvalSession.benchmark)
        .all()
    )

    models = sorted({r.model_version for r in rows})
    benchmarks = sorted({r.benchmark for r in rows})

    # Build lookup
    lookup: dict[tuple[str, str], float] = {}
    for r in rows:
        total = int(r.total or 0)
        errors = int(r.errors or 0)
        rate = errors / total if total > 0 else 0.0
        lookup[(r.model_version, r.benchmark)] = round(rate, 4)

    matrix = [
        [lookup.get((m, b), 0.0) for b in benchmarks]
        for m in models
    ]

    return {
        "models": models,
        "benchmarks": benchmarks,
        "matrix": matrix,
    }


def get_systematic_weaknesses(db: Session) -> dict[str, Any]:
    """
    Identify error types that appear across multiple benchmarks (systematic weaknesses).

    An error type is "systematic" if it appears in 2+ benchmarks.
    """
    rows = (
        db.query(
            sqlfunc.split_part(ErrorTag.tag_path, ".", 1).label("l1_type"),
            EvalRecord.benchmark,
            sqlfunc.count(ErrorTag.id).label("cnt"),
        )
        .join(EvalRecord, EvalRecord.id == ErrorTag.record_id)
        .group_by(
            sqlfunc.split_part(ErrorTag.tag_path, ".", 1),
            EvalRecord.benchmark,
        )
        .all()
    )

    # Aggregate: error_type -> {benchmarks, total_frequency}
    agg: dict[str, dict] = {}
    for r in rows:
        et = r.l1_type or "(unknown)"
        if et not in agg:
            agg[et] = {"benchmarks": set(), "frequency": 0}
        agg[et]["benchmarks"].add(r.benchmark)
        agg[et]["frequency"] += r.cnt

    # Filter to systematic (2+ benchmarks), sort by frequency desc
    weaknesses = [
        {
            "error_type": et,
            "benchmarks": sorted(info["benchmarks"]),
            "frequency": info["frequency"],
        }
        for et, info in agg.items()
        if len(info["benchmarks"]) >= 2
    ]
    weaknesses.sort(key=lambda w: w["frequency"], reverse=True)

    return {"weaknesses": weaknesses}


def get_error_trends(
    db: Session,
    benchmark: Optional[str],
    model_version: Optional[str],
) -> dict[str, Any]:
    """
    Return error rate trend over time (grouped by month).
    """
    q = db.query(
        sqlfunc.to_char(EvalSession.created_at, "YYYY-MM").label("period"),
        sqlfunc.sum(EvalSession.total_count).label("total"),
        sqlfunc.sum(EvalSession.error_count).label("errors"),
    )
    if benchmark:
        q = q.filter(EvalSession.benchmark == benchmark)
    if model_version:
        q = q.filter(EvalSession.model_version == model_version)

    rows = (
        q.group_by(sqlfunc.to_char(EvalSession.created_at, "YYYY-MM"))
        .order_by(sqlfunc.to_char(EvalSession.created_at, "YYYY-MM"))
        .all()
    )

    data_points = []
    for r in rows:
        total = int(r.total or 0)
        errors = int(r.errors or 0)
        rate = errors / total if total > 0 else 0.0
        data_points.append({
            "period": r.period,
            "error_rate": round(rate, 4),
            "total": total,
            "errors": errors,
        })

    return {"data_points": data_points}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/services/test_cross_benchmark.py -x -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/cross_benchmark.py backend/app/schemas/cross_benchmark.py backend/tests/services/test_cross_benchmark.py
git commit -m "feat(query): add cross-benchmark matrix, weakness detection, and trend analysis"
```

---

## Phase 5 — Report Builder Service + Celery Task

### Task 5.1 — Write failing test for report builder

**Files:**
- Create: `backend/tests/services/test_report_builder.py`
- Create: `backend/app/services/report_builder.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/services/test_report_builder.py
"""Unit tests for report builder service."""
import pytest
import uuid
from app.services.report_builder import build_summary_report, build_comparison_report


def test_build_summary_report(db_session):
    result = build_summary_report(
        db=db_session,
        session_ids=None,
        benchmark=None,
        model_version=None,
    )
    assert "summary" in result
    assert "error_distribution" in result
    assert "top_errors" in result
    assert "generated_at" in result


def test_build_summary_report_filtered(db_session):
    result = build_summary_report(
        db=db_session,
        session_ids=None,
        benchmark="mmlu",
        model_version="v1",
    )
    assert "summary" in result


def test_build_comparison_report(db_session):
    result = build_comparison_report(
        db=db_session,
        version_a="v1",
        version_b="v2",
        benchmark=None,
    )
    assert "comparison" in result
    assert "diff" in result
    assert "radar" in result
    assert "generated_at" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/services/test_report_builder.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 5.2 — Implement report builder

- [ ] **Step 3: Write `app/services/report_builder.py`**

```python
# backend/app/services/report_builder.py
"""Build structured report content by composing query services."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional
import uuid
from sqlalchemy.orm import Session

from app.services.analysis_query import get_analysis_summary, get_error_distribution
from app.services.compare import compare_versions, get_version_diff, get_radar_data


def build_summary_report(
    db: Session,
    session_ids: Optional[list[uuid.UUID]],
    benchmark: Optional[str],
    model_version: Optional[str],
) -> dict[str, Any]:
    """Build a summary report composing analysis overview + distribution."""
    summary = get_analysis_summary(
        db=db,
        benchmark=benchmark,
        model_version=model_version,
        time_range_start=None,
        time_range_end=None,
    )

    error_dist = get_error_distribution(
        db=db,
        group_by="error_type",
        benchmark=benchmark,
        model_version=model_version,
    )

    # Top 10 most frequent errors
    top_errors = sorted(error_dist, key=lambda x: x["count"], reverse=True)[:10]

    return {
        "summary": summary,
        "error_distribution": error_dist,
        "top_errors": top_errors,
        "filters": {
            "benchmark": benchmark,
            "model_version": model_version,
            "session_ids": [str(s) for s in session_ids] if session_ids else None,
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


def build_comparison_report(
    db: Session,
    version_a: str,
    version_b: str,
    benchmark: Optional[str],
) -> dict[str, Any]:
    """Build a comparison report between two model versions."""
    comparison = compare_versions(db, version_a, version_b, benchmark)
    diff = get_version_diff(db, version_a, version_b, benchmark)
    radar = get_radar_data(db, version_a, version_b, benchmark)

    return {
        "comparison": comparison,
        "diff": diff,
        "radar": radar,
        "generated_at": datetime.utcnow().isoformat(),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/services/test_report_builder.py -x -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/report_builder.py backend/tests/services/test_report_builder.py
git commit -m "feat(report): add report builder composing analysis and comparison services"
```

### Task 5.3 — Write failing test for generate_report Celery task

**Files:**
- Create: `backend/tests/tasks/test_generate_report.py`
- Create: `backend/app/tasks/report.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/tasks/test_generate_report.py
"""Unit tests for generate_report Celery task."""
import pytest
import uuid
from unittest.mock import patch, MagicMock
from app.tasks.report import generate_report


def test_generate_summary_report(db_session):
    """Test that generate_report creates a report row in the DB."""
    report_id = str(uuid.uuid4())

    with patch("app.tasks.report.get_db_session") as mock_get_db:
        mock_get_db.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        result = generate_report(
            report_id=report_id,
            report_type="summary",
            config={
                "title": "Test Summary Report",
                "benchmark": None,
                "model_version": None,
                "session_ids": None,
            },
        )

    assert result["status"] == "done"
    assert result["report_id"] == report_id


def test_generate_comparison_report(db_session):
    report_id = str(uuid.uuid4())

    with patch("app.tasks.report.get_db_session") as mock_get_db:
        mock_get_db.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        result = generate_report(
            report_id=report_id,
            report_type="comparison",
            config={
                "title": "Test Comparison Report",
                "version_a": "v1",
                "version_b": "v2",
                "benchmark": None,
            },
        )

    assert result["status"] == "done"
    assert result["report_id"] == report_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/tasks/test_generate_report.py -x`
Expected: FAIL with `ModuleNotFoundError`

### Task 5.4 — Implement generate_report Celery task

- [ ] **Step 3: Write `app/tasks/report.py`**

```python
# backend/app/tasks/report.py
"""Celery task for generating analysis reports."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from celery import shared_task

from app.db.session import get_db_session
from app.models.report import Report
from app.services.report_builder import build_summary_report, build_comparison_report


@shared_task(
    name="tasks.report.generate_report",
    bind=True,
    max_retries=1,
)
def generate_report(
    self,
    report_id: str,
    report_type: str,
    config: dict[str, Any],
) -> dict:
    """
    Generate a report and store it in the reports table.

    Args:
        report_id: Pre-created report UUID (status=pending).
        report_type: 'summary' | 'comparison' | 'cross_benchmark'
        config: Report parameters (title, filters, versions, etc.)
    """
    with get_db_session() as db:
        # Update report status to generating
        report = db.get(Report, uuid.UUID(report_id))
        if report:
            report.status = "generating"
            db.commit()

        try:
            if report_type == "summary":
                content = build_summary_report(
                    db=db,
                    session_ids=config.get("session_ids"),
                    benchmark=config.get("benchmark"),
                    model_version=config.get("model_version"),
                )
            elif report_type == "comparison":
                content = build_comparison_report(
                    db=db,
                    version_a=config["version_a"],
                    version_b=config["version_b"],
                    benchmark=config.get("benchmark"),
                )
            elif report_type == "cross_benchmark":
                from app.services.cross_benchmark import (
                    get_benchmark_matrix,
                    get_systematic_weaknesses,
                )
                content = {
                    "matrix": get_benchmark_matrix(db),
                    "weaknesses": get_systematic_weaknesses(db),
                    "generated_at": datetime.utcnow().isoformat(),
                }
            else:
                raise ValueError(f"Unknown report_type: {report_type}")

            # Write report content
            if report:
                report.content = content
                report.status = "done"
                report.updated_at = datetime.utcnow()
            else:
                # Create report row if it wasn't pre-created
                report = Report(
                    id=uuid.UUID(report_id),
                    title=config.get("title", f"{report_type} report"),
                    report_type=report_type,
                    content=content,
                    status="done",
                    benchmark=config.get("benchmark"),
                    model_version=config.get("model_version"),
                )
                db.add(report)

            db.commit()
            return {"status": "done", "report_id": report_id}

        except Exception as exc:
            if report:
                report.status = "failed"
                report.error_message = str(exc)
                db.commit()
            return {"status": "failed", "report_id": report_id, "error": str(exc)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/tasks/test_generate_report.py -x -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/tasks/report.py backend/tests/tasks/test_generate_report.py
git commit -m "feat(report): add generate_report Celery task with summary and comparison builders"
```

---

## Phase 6 — Report Schemas

### Task 6.1 — Write report Pydantic schemas

**Files:**
- Create: `backend/app/schemas/report.py`

- [ ] **Step 1: Write `app/schemas/report.py`**

```python
# backend/app/schemas/report.py
"""Pydantic schemas for report API."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    report_type: str = Field(..., pattern=r"^(summary|comparison|cross_benchmark)$")
    benchmark: Optional[str] = None
    model_version: Optional[str] = None
    session_ids: Optional[list[uuid.UUID]] = None
    # For comparison reports
    version_a: Optional[str] = None
    version_b: Optional[str] = None


class ReportGenerateResponse(BaseModel):
    report_id: uuid.UUID
    status: str = "pending"
    message: str = ""


class ReportResponse(BaseModel):
    id: uuid.UUID
    title: str
    report_type: str
    status: str
    content: dict[str, Any] = Field(default_factory=dict)
    benchmark: Optional[str]
    model_version: Optional[str]
    error_message: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListItem(BaseModel):
    id: uuid.UUID
    title: str
    report_type: str
    status: str
    benchmark: Optional[str]
    model_version: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/schemas/report.py
git commit -m "feat(report): add Pydantic schemas for report API"
```

---

## Phase 7 — REST API Routers

### Task 7.1 — Analysis API router

**Files:**
- Create: `backend/app/api/v1/routers/analysis.py`
- Create: `backend/tests/api/test_analysis_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_analysis_api.py
import pytest
from httpx import AsyncClient


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-viewer-token"}


@pytest.mark.anyio
async def test_analysis_summary(async_client: AsyncClient, auth_headers):
    resp = await async_client.get("/api/v1/analysis/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_sessions" in data
    assert "accuracy" in data


@pytest.mark.anyio
async def test_analysis_summary_with_filters(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/analysis/summary?benchmark=mmlu&model_version=v1",
        headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_error_distribution_by_error_type(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/analysis/error-distribution?group_by=error_type",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_error_distribution_invalid_group_by(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/analysis/error-distribution?group_by=invalid",
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_error_records_paginated(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/analysis/records?page=1&size=10",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.anyio
async def test_record_detail_not_found(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/analysis/records/00000000-0000-0000-0000-000000000099/detail",
        headers=auth_headers,
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Write the router**

```python
# backend/app/api/v1/routers/analysis.py
"""Analysis query endpoints: summary, distribution, records, detail."""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.analysis_query import (
    get_analysis_summary,
    get_error_distribution,
    get_error_records_page,
    get_record_detail,
)
from app.schemas.analysis_query import (
    AnalysisSummary,
    DistributionItem,
    PaginatedRecords,
    RecordDetail,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/summary", response_model=AnalysisSummary)
def analysis_summary(
    benchmark: Optional[str] = None,
    model_version: Optional[str] = None,
    time_range_start: Optional[datetime] = None,
    time_range_end: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    return get_analysis_summary(db, benchmark, model_version, time_range_start, time_range_end)


@router.get("/error-distribution", response_model=list[DistributionItem])
def error_distribution(
    group_by: str = Query(..., pattern=r"^(error_type|category|severity)$"),
    benchmark: Optional[str] = None,
    model_version: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return get_error_distribution(db, group_by, benchmark, model_version)


@router.get("/records", response_model=PaginatedRecords)
def error_records(
    error_type: Optional[str] = None,
    benchmark: Optional[str] = None,
    model_version: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return get_error_records_page(db, error_type, benchmark, model_version, page, size)


@router.get("/records/{record_id}/detail", response_model=RecordDetail)
def record_detail(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    result = get_record_detail(db, record_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return result
```

- [ ] **Step 3: Run test**

Run: `cd backend && python -m pytest tests/api/test_analysis_api.py -x -v`
Expected: 6 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/routers/analysis.py backend/tests/api/test_analysis_api.py
git commit -m "feat(api): add analysis query endpoints (summary, distribution, records, detail)"
```

### Task 7.2 — Compare API router

**Files:**
- Create: `backend/app/api/v1/routers/compare.py`
- Create: `backend/tests/api/test_compare_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_compare_api.py
import pytest
from httpx import AsyncClient


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-viewer-token"}


@pytest.mark.anyio
async def test_compare_versions(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/compare/versions?version_a=v1&version_b=v2",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version_a"] == "v1"
    assert data["version_b"] == "v2"


@pytest.mark.anyio
async def test_compare_versions_with_benchmark(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/compare/versions?version_a=v1&version_b=v2&benchmark=mmlu",
        headers=auth_headers,
    )
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_compare_diff(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/compare/diff?version_a=v1&version_b=v2",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "regressed" in data
    assert "improved" in data


@pytest.mark.anyio
async def test_compare_radar(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/compare/radar?version_a=v1&version_b=v2",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "dimensions" in data
    assert "scores_a" in data


@pytest.mark.anyio
async def test_compare_requires_both_versions(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/compare/versions?version_a=v1",
        headers=auth_headers,
    )
    assert resp.status_code == 422  # missing version_b
```

- [ ] **Step 2: Write the router**

```python
# backend/app/api/v1/routers/compare.py
"""Version comparison endpoints: compare, diff, radar."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.compare import compare_versions, get_version_diff, get_radar_data
from app.schemas.compare import VersionComparison, VersionDiff, RadarData

router = APIRouter(prefix="/compare", tags=["compare"])


@router.get("/versions", response_model=VersionComparison)
def versions(
    version_a: str = Query(...),
    version_b: str = Query(...),
    benchmark: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return compare_versions(db, version_a, version_b, benchmark)


@router.get("/diff", response_model=VersionDiff)
def diff(
    version_a: str = Query(...),
    version_b: str = Query(...),
    benchmark: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return get_version_diff(db, version_a, version_b, benchmark)


@router.get("/radar", response_model=RadarData)
def radar(
    version_a: str = Query(...),
    version_b: str = Query(...),
    benchmark: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return get_radar_data(db, version_a, version_b, benchmark)
```

- [ ] **Step 3: Run test**

Run: `cd backend && python -m pytest tests/api/test_compare_api.py -x -v`
Expected: 5 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/routers/compare.py backend/tests/api/test_compare_api.py
git commit -m "feat(api): add version comparison endpoints (versions, diff, radar)"
```

### Task 7.3 — Cross-Benchmark + Trends API routers

**Files:**
- Create: `backend/app/api/v1/routers/cross_benchmark.py`
- Create: `backend/app/api/v1/routers/trends.py`
- Create: `backend/tests/api/test_cross_benchmark_api.py`
- Create: `backend/tests/api/test_trends_api.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/api/test_cross_benchmark_api.py
import pytest
from httpx import AsyncClient


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-viewer-token"}


@pytest.mark.anyio
async def test_benchmark_matrix(async_client: AsyncClient, auth_headers):
    resp = await async_client.get("/api/v1/cross-benchmark/matrix", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert "benchmarks" in data
    assert "matrix" in data


@pytest.mark.anyio
async def test_systematic_weaknesses(async_client: AsyncClient, auth_headers):
    resp = await async_client.get("/api/v1/cross-benchmark/weakness", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "weaknesses" in data
```

```python
# backend/tests/api/test_trends_api.py
import pytest
from httpx import AsyncClient


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-viewer-token"}


@pytest.mark.anyio
async def test_trends(async_client: AsyncClient, auth_headers):
    resp = await async_client.get("/api/v1/trends", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "data_points" in data


@pytest.mark.anyio
async def test_trends_with_filters(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/trends?benchmark=mmlu&model_version=v1",
        headers=auth_headers,
    )
    assert resp.status_code == 200
```

- [ ] **Step 2: Write the routers**

```python
# backend/app/api/v1/routers/cross_benchmark.py
"""Cross-benchmark analysis endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.cross_benchmark import get_benchmark_matrix, get_systematic_weaknesses
from app.schemas.cross_benchmark import BenchmarkMatrix, SystematicWeaknesses

router = APIRouter(prefix="/cross-benchmark", tags=["cross-benchmark"])


@router.get("/matrix", response_model=BenchmarkMatrix)
def matrix(db: Session = Depends(get_db)):
    return get_benchmark_matrix(db)


@router.get("/weakness", response_model=SystematicWeaknesses)
def weakness(db: Session = Depends(get_db)):
    return get_systematic_weaknesses(db)
```

```python
# backend/app/api/v1/routers/trends.py
"""Error rate trends endpoint."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.cross_benchmark import get_error_trends
from app.schemas.cross_benchmark import ErrorTrends

router = APIRouter(tags=["trends"])


@router.get("/trends", response_model=ErrorTrends)
def trends(
    benchmark: Optional[str] = None,
    model_version: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return get_error_trends(db, benchmark, model_version)
```

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest tests/api/test_cross_benchmark_api.py tests/api/test_trends_api.py -x -v`
Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/routers/cross_benchmark.py backend/app/api/v1/routers/trends.py backend/tests/api/test_cross_benchmark_api.py backend/tests/api/test_trends_api.py
git commit -m "feat(api): add cross-benchmark matrix, weakness, and trends endpoints"
```

### Task 7.4 — Reports API router

**Files:**
- Create: `backend/app/api/v1/routers/reports.py`
- Create: `backend/tests/api/test_reports_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/api/test_reports_api.py
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-analyst-token"}


@pytest.mark.anyio
async def test_generate_report(async_client: AsyncClient, auth_headers):
    with patch("app.api.v1.routers.reports.generate_report") as mock_task:
        mock_result = MagicMock()
        mock_result.id = "celery-report-uuid-123"
        mock_task.apply_async.return_value = mock_result

        resp = await async_client.post(
            "/api/v1/reports/generate",
            json={
                "title": "Test Report",
                "report_type": "summary",
            },
            headers=auth_headers,
        )
    assert resp.status_code == 202
    assert "report_id" in resp.json()


@pytest.mark.anyio
async def test_list_reports(async_client: AsyncClient, auth_headers):
    resp = await async_client.get("/api/v1/reports", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.anyio
async def test_get_report_not_found(async_client: AsyncClient, auth_headers):
    resp = await async_client.get(
        "/api/v1/reports/00000000-0000-0000-0000-000000000099",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_generate_requires_analyst(async_client: AsyncClient):
    viewer_headers = {"Authorization": "Bearer test-viewer-token"}
    resp = await async_client.post(
        "/api/v1/reports/generate",
        json={"title": "Test", "report_type": "summary"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403
```

- [ ] **Step 2: Write the router**

```python
# backend/app/api/v1/routers/reports.py
"""Report generation and retrieval endpoints."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.deps import require_role
from app.models.report import Report
from app.tasks.report import generate_report
from app.schemas.report import (
    ReportGenerateRequest,
    ReportGenerateResponse,
    ReportResponse,
    ReportListItem,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_report(
    payload: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["analyst", "admin"])),
):
    """Create a report row (pending) and dispatch generation to Celery."""
    report = Report(
        title=payload.title,
        report_type=payload.report_type,
        benchmark=payload.benchmark,
        model_version=payload.model_version,
        session_ids=[str(s) for s in payload.session_ids] if payload.session_ids else None,
        status="pending",
        created_by=current_user.username,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    config = {
        "title": payload.title,
        "benchmark": payload.benchmark,
        "model_version": payload.model_version,
        "session_ids": [str(s) for s in payload.session_ids] if payload.session_ids else None,
    }
    if payload.report_type == "comparison":
        config["version_a"] = payload.version_a
        config["version_b"] = payload.version_b

    generate_report.apply_async(
        kwargs=dict(
            report_id=str(report.id),
            report_type=payload.report_type,
            config=config,
        ),
    )

    return ReportGenerateResponse(
        report_id=report.id,
        status="pending",
        message=f"Report generation dispatched: {payload.title}",
    )


@router.get("", response_model=list[ReportListItem])
def list_reports(db: Session = Depends(get_db)):
    return (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .limit(100)
        .all()
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: uuid.UUID, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
```

- [ ] **Step 3: Run test**

Run: `cd backend && python -m pytest tests/api/test_reports_api.py -x -v`
Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/v1/routers/reports.py backend/tests/api/test_reports_api.py
git commit -m "feat(api): add report generation and retrieval endpoints"
```

---

## Phase 8 — Register Routers in FastAPI App

### Task 8.1 — Add router imports and registration

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add router imports and registration**

```python
# Add to existing imports in app/main.py:
from app.api.v1.routers.analysis import router as analysis_router
from app.api.v1.routers.compare import router as compare_router
from app.api.v1.routers.cross_benchmark import router as cross_benchmark_router
from app.api.v1.routers.trends import router as trends_router
from app.api.v1.routers.reports import router as reports_router

# Add inside create_app() or at module level:
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(compare_router, prefix="/api/v1")
app.include_router(cross_benchmark_router, prefix="/api/v1")
app.include_router(trends_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
```

- [ ] **Step 2: Run full test suite**

Run: `cd backend && python -m pytest tests/ -x --tb=short`
Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(api): register analysis, compare, cross-benchmark, trends, and reports routers"
```

---

## Phase 9 — Final Integration Check

### Task 9.1 — Run full test suite

- [ ] **Step 1: Run all tests**

```bash
cd backend && python -m pytest tests/ -v --tb=short
# Expected: all tests pass, 0 failures
```

### Task 9.2 — Verify Celery task registration

- [ ] **Step 2: Check task is registered**

```bash
cd backend && celery -A app.celery_app inspect registered
# Expected output includes: tasks.report.generate_report
```

### Task 9.3 — Verify API routes exist

- [ ] **Step 3: Check all query/report routes**

```bash
cd backend && python -c "
from app.main import app
routes = [r.path for r in app.routes]
expected = [
    '/api/v1/analysis/summary',
    '/api/v1/analysis/error-distribution',
    '/api/v1/analysis/records',
    '/api/v1/compare/versions',
    '/api/v1/compare/diff',
    '/api/v1/compare/radar',
    '/api/v1/cross-benchmark/matrix',
    '/api/v1/cross-benchmark/weakness',
    '/api/v1/trends',
    '/api/v1/reports',
    '/api/v1/reports/generate',
]
for ep in expected:
    match = any(ep in r for r in routes)
    status = 'OK' if match else 'MISSING'
    print(f'  {status}: {ep}')
assert all(any(ep in r for r in routes) for ep in expected), 'Some routes missing!'
print('All query/report routes registered OK')
"
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "chore(query): final integration checks for Query & Aggregation Layer + Report Agent"
```

---

## Dependencies on Earlier Plans

| Symbol | Location | Used by |
|---|---|---|
| `Base` (DeclarativeBase) | `app/db/base.py` | `Report` ORM model |
| `get_db` (session dep) | `app/db/session.py` | All API routers |
| `get_db_session` (sync context mgr) | `app/db/session.py` | `generate_report` Celery task |
| `require_role` | `app/api/v1/deps.py` | Reports router (Analyst+) |
| `app` (FastAPI) | `app/main.py` | Router registration |
| `EvalSession` | `app/models/eval_session.py` | All query services |
| `EvalRecord` | `app/models/eval_record.py` | All query services |
| `AnalysisResult` | `app/models/analysis_result.py` | Analysis query, cost summary |
| `ErrorTag` | `app/models/error_tag.py` | Distribution, weakness, comparison |
| Celery app | `app/celery_app.py` | `@shared_task` for `generate_report` |
| All domain tables | Alembic migrations (Plans 1-4) | ORM queries |
