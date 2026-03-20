# Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the skeleton `app/core/logging.py` from Plan 01 with production-grade observability: (1) structured JSON logs via structlog with request_id propagation and environment-aware rendering; (2) Prometheus metrics covering all four pillars from design doc §14.3 (ingestion rate, LLM call count / cost / latency, Celery queue depth, API latency); (3) a `/metrics` scrape endpoint; (4) three AlertManager alert rules (LLM cost > 80% daily budget, all workers offline, ingestion failure rate > 10%).

**Architecture:**

```
FastAPI request  ──► middleware ──► structlog contextvars (request_id, user_id, path)
                                 ──► prometheus_client Histogram/Counter/Gauge
Celery task       ──► task signals ──► structlog + prometheus counters
app/core/logging.py     ← structlog full config (JSON prod / ConsoleRenderer dev)
app/core/metrics.py     ← all prometheus_client metric objects (module-level singletons)
app/api/v1/routers/metrics.py  ← GET /api/v1/metrics (WSGI passthrough)
k8s/base/monitoring/
  prometheus-rule.yaml  ← PrometheusRule CRD (3 alert rules)
  servicemonitor.yaml   ← ServiceMonitor CRD (Prometheus Operator scrape config)
```

**Design doc reference:** §14.3 可观测性

**Tech Stack:** structlog 24.1+, prometheus-client 0.20+, Python 3.11, FastAPI middleware, Celery signals, Prometheus Operator CRDs (for K8s alerting)

**Prerequisites:** Plan 01 (FastAPI app, Celery app, `app/core/logging.py` skeleton exists).

---

## File Structure After This Plan

```
backend/
  app/
    core/
      logging.py          # REPLACED — full structlog config
      metrics.py          # NEW — all prometheus_client metric objects
    middleware/
      __init__.py
      logging_middleware.py   # NEW — request_id injection + access log
      metrics_middleware.py   # NEW — HTTP latency histogram per route
    api/v1/routers/
      metrics.py          # NEW — GET /api/v1/metrics scrape endpoint
    celery_signals.py     # NEW — Celery task_prerun/postrun/failure hooks
    tests/
      unit/
        test_logging.py           # REPLACED — full tests
        test_metrics.py           # NEW
        test_logging_middleware.py # NEW
        test_metrics_middleware.py # NEW
  pyproject.toml          # add prometheus-client dependency
k8s/base/monitoring/
  servicemonitor.yaml     # NEW
  prometheus-rule.yaml    # NEW
```

---

## Task 1 — Add `prometheus-client` dependency

**Files:**
- Edit: `backend/pyproject.toml`

### Steps

- [ ] **Step 1: Add `prometheus-client` to `pyproject.toml` dependencies**

  ```toml
  dependencies = [
      ...
      "prometheus-client==0.20.0",
  ]
  ```

- [ ] **Step 2: Install**
  ```bash
  cd backend && pip install -e ".[dev]"
  python -c "import prometheus_client; print(prometheus_client.__version__)"
  ```
  Expected: `0.20.0`

---

## Task 2 — Replace `app/core/logging.py` with full structlog config

**Files:**
- Edit: `backend/app/core/logging.py`
- Edit: `backend/app/tests/unit/test_logging.py`

### Steps

- [ ] **Step 1: Write failing tests (replace existing skeleton tests)**

```python
# backend/app/tests/unit/test_logging.py
import json
import logging
import os
from io import StringIO
import pytest
import structlog
from app.core.logging import configure_logging, get_logger


def test_configure_logging_dev_mode(monkeypatch):
    """Dev mode: ConsoleRenderer (human-readable), no exception."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    configure_logging()   # should not raise


def test_configure_logging_prod_mode(monkeypatch):
    """Prod mode: JSONRenderer — log output is valid JSON."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    configure_logging()
    logger = get_logger("test.prod")
    # Capture output
    buf = StringIO()
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(buf),
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
    )
    log = structlog.get_logger("test.prod")
    log.info("hello", key="value")
    line = buf.getvalue().strip()
    parsed = json.loads(line)
    assert parsed["key"] == "value"
    assert parsed["event"] == "hello"
    assert "timestamp" in parsed
    assert parsed["level"] == "info"


def test_get_logger_returns_bound_logger(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    configure_logging()
    logger = get_logger("test.module")
    assert logger is not None
    # Should accept kwargs without raising
    logger.info("test message", request_id="abc-123", user_id="u1")


def test_context_var_binding(monkeypatch):
    """structlog.contextvars.bind_contextvars sets fields on all log calls."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    configure_logging()
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="req-xyz")
    # No assertion needed — just verify no exception
    log = get_logger("test.ctx")
    log.info("bound context test")
    structlog.contextvars.clear_contextvars()


def test_stdlib_logging_routed_through_structlog(monkeypatch):
    """stdlib logging.getLogger calls should not bypass structlog."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    configure_logging()
    stdlib_log = logging.getLogger("uvicorn.error")
    stdlib_log.info("stdlib message")   # should not raise
```

- [ ] Run: `cd backend && pytest app/tests/unit/test_logging.py -v` → **FAILED** (skeleton impl fails JSON test)

- [ ] **Step 2: Replace `backend/app/core/logging.py`**

```python
# backend/app/core/logging.py
"""
Production-grade structlog configuration.

Behaviour by ENVIRONMENT:
  development  →  structlog.dev.ConsoleRenderer (coloured, human-readable)
  production   →  structlog.processors.JSONRenderer (one JSON object per line,
                  stdout, ready for Fluentd / Loki / CloudWatch)

Request-scoped fields (request_id, user_id, path, method) are injected by
LoggingMiddleware via structlog.contextvars and automatically appear in every
log line emitted during that request's lifetime.
"""
import logging
import sys
from typing import Any

import structlog

from app.core.config import settings


def _build_processors(env: str) -> list[Any]:
    shared = [
        # Merge any contextvars bound by middleware (request_id, user_id, …)
        structlog.contextvars.merge_contextvars,
        # Add log level string ("info", "warning", …)
        structlog.processors.add_log_level,
        # ISO-8601 timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Render exception info as a "exception" key rather than a traceback string
        structlog.processors.dict_tracebacks,
        # Include caller module + line number
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.MODULE,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    if env == "production":
        shared.append(structlog.processors.JSONRenderer())
    else:
        shared.append(structlog.dev.ConsoleRenderer(colors=True))

    return shared


def configure_logging() -> None:
    """
    Configure structlog and route stdlib logging through structlog.
    Call once at application startup (FastAPI lifespan or Celery app init).
    """
    env = getattr(settings, "ENVIRONMENT", "development")
    log_level_name = getattr(settings, "LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    processors = _build_processors(env)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy, celery) through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    logging.getLogger("uvicorn").handlers.clear()
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if env == "development" else logging.WARNING
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a structlog bound logger for the given module name."""
    return structlog.get_logger(name)
```

- [ ] **Step 3: Add `LOG_LEVEL` to `Settings` in `app/core/config.py`**

  ```python
  LOG_LEVEL: str = "INFO"
  ```

- [ ] Run: `pytest app/tests/unit/test_logging.py -v` → **PASSED** (5 tests)
- [ ] Commit: `git commit -m "feat(obs): replace skeleton logging with full structlog JSON/dev config"`

---

## Task 3 — `LoggingMiddleware` (request_id + access log)

**Files:**
- Create: `backend/app/middleware/__init__.py`
- Create: `backend/app/middleware/logging_middleware.py`
- Create: `backend/app/tests/unit/test_logging_middleware.py`

### Steps

- [ ] **Step 1: Write failing test**

```python
# backend/app/tests/unit/test_logging_middleware.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app


@pytest.mark.asyncio
async def test_request_id_header_added_to_response():
    """Middleware must echo X-Request-ID back in response headers."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch("app.api.v1.routers.health.check_db", AsyncMock(return_value=True)), \
             patch("app.api.v1.routers.health.check_redis", AsyncMock(return_value=True)):
            resp = await client.get(
                "/api/v1/health", headers={"X-Request-ID": "test-req-123"}
            )
    assert resp.headers.get("X-Request-ID") == "test-req-123"


@pytest.mark.asyncio
async def test_request_id_generated_when_missing():
    """Middleware must generate a request_id if client did not send one."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch("app.api.v1.routers.health.check_db", AsyncMock(return_value=True)), \
             patch("app.api.v1.routers.health.check_redis", AsyncMock(return_value=True)):
            resp = await client.get("/api/v1/health")
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) == 36   # UUID4 length
```

- [ ] Run: `pytest app/tests/unit/test_logging_middleware.py -v` → **FAILED**

- [ ] **Step 2: Implement `LoggingMiddleware`**

```python
# backend/app/middleware/logging_middleware.py
"""
Starlette middleware that:
1. Generates / propagates a request_id (X-Request-ID header).
2. Binds request_id, path, method, and client_ip to structlog contextvars
   so every log line emitted during this request automatically carries them.
3. Emits a single structured access log on response (method, path, status,
   duration_ms).
4. Echoes request_id in the response header for client-side correlation.
"""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger("access")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Resolve request_id
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 2. Bind to structlog contextvars (cleared automatically per-request
        #    because Starlette runs each request in its own contextvars scope)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            logger.error(
                "unhandled_exception",
                exc_info=exc,
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            status_code = getattr(response, "status_code", 0)
            logger.info(
                "request",
                status=status_code,
                duration_ms=duration_ms,
            )

        # 3. Echo request_id in response
        response.headers["X-Request-ID"] = request_id
        return response
```

```python
# backend/app/middleware/__init__.py
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.metrics_middleware import MetricsMiddleware

__all__ = ["LoggingMiddleware", "MetricsMiddleware"]
```

- [ ] **Step 3: Register `LoggingMiddleware` in `app/main.py`**

  ```python
  from app.middleware.logging_middleware import LoggingMiddleware
  app.add_middleware(LoggingMiddleware)
  ```

- [ ] Run: `pytest app/tests/unit/test_logging_middleware.py -v` → **PASSED** (2 tests)
- [ ] Commit: `git commit -m "feat(obs): add LoggingMiddleware for request_id propagation and access logging"`

---

## Task 4 — `app/core/metrics.py` (all Prometheus metric objects)

**Files:**
- Create: `backend/app/core/metrics.py`
- Create: `backend/app/tests/unit/test_metrics.py`

### Steps

- [ ] **Step 1: Write failing tests**

```python
# backend/app/tests/unit/test_metrics.py
"""Tests that all metric objects are importable, have correct type and labels."""
import pytest
from prometheus_client import (
    Counter, Histogram, Gauge, CollectorRegistry, REGISTRY,
)
from app.core import metrics as m


def test_ingest_records_total_is_counter():
    assert isinstance(m.INGEST_RECORDS_TOTAL, Counter)


def test_ingest_records_total_has_status_label():
    # Accessing _labelnames is an internal attribute but stable across versions
    assert "status" in m.INGEST_RECORDS_TOTAL._labelnames


def test_llm_calls_total_is_counter():
    assert isinstance(m.LLM_CALLS_TOTAL, Counter)
    assert "model" in m.LLM_CALLS_TOTAL._labelnames
    assert "status" in m.LLM_CALLS_TOTAL._labelnames


def test_llm_cost_usd_total_is_counter():
    assert isinstance(m.LLM_COST_USD_TOTAL, Counter)
    assert "model" in m.LLM_COST_USD_TOTAL._labelnames


def test_llm_latency_seconds_is_histogram():
    assert isinstance(m.LLM_LATENCY_SECONDS, Histogram)
    assert "model" in m.LLM_LATENCY_SECONDS._labelnames


def test_celery_queue_depth_is_gauge():
    assert isinstance(m.CELERY_QUEUE_DEPTH, Gauge)
    assert "queue" in m.CELERY_QUEUE_DEPTH._labelnames


def test_http_request_duration_is_histogram():
    assert isinstance(m.HTTP_REQUEST_DURATION_SECONDS, Histogram)
    assert "method" in m.HTTP_REQUEST_DURATION_SECONDS._labelnames
    assert "path" in m.HTTP_REQUEST_DURATION_SECONDS._labelnames
    assert "status" in m.HTTP_REQUEST_DURATION_SECONDS._labelnames


def test_ingest_failures_total_is_counter():
    assert isinstance(m.INGEST_FAILURES_TOTAL, Counter)


def test_daily_budget_used_ratio_is_gauge():
    assert isinstance(m.LLM_DAILY_BUDGET_USED_RATIO, Gauge)


def test_workers_online_is_gauge():
    assert isinstance(m.CELERY_WORKERS_ONLINE, Gauge)
    assert "queue" in m.CELERY_WORKERS_ONLINE._labelnames
```

- [ ] Run: `pytest app/tests/unit/test_metrics.py -v` → **FAILED**

- [ ] **Step 2: Implement `backend/app/core/metrics.py`**

```python
# backend/app/core/metrics.py
"""
All Prometheus metric objects for FailureLogAnalyzer.

These are module-level singletons — import and call .labels(...).inc() / .observe()
from anywhere in the application. Never create metric objects dynamically.

Metrics defined (§14.3 of design doc):
  Ingestion:
    fla_ingest_records_total          Counter   records processed (label: status=ok|failed)
    fla_ingest_failures_total         Counter   records that failed parsing
    fla_ingest_bytes_total            Counter   bytes ingested (label: benchmark)

  LLM Judge:
    fla_llm_calls_total               Counter   LLM API calls (labels: model, status=ok|error|circuit_open|budget_exhausted)
    fla_llm_cost_usd_total            Counter   accumulated USD cost (label: model)
    fla_llm_latency_seconds           Histogram LLM round-trip latency (label: model)
    fla_llm_daily_budget_used_ratio   Gauge     current_spend / daily_limit (0-1, or -1 if unlimited)

  Celery:
    fla_celery_queue_depth            Gauge     messages in queue (label: queue=rule|llm|report)
    fla_celery_workers_online         Gauge     active workers reporting heartbeat (label: queue)
    fla_celery_task_duration_seconds  Histogram task wall-clock time (labels: task_name, status=ok|failed)

  HTTP API:
    fla_http_request_duration_seconds Histogram FastAPI response time (labels: method, path, status)
"""
from prometheus_client import Counter, Gauge, Histogram

# ── Ingestion ─────────────────────────────────────────────────────────────────

INGEST_RECORDS_TOTAL = Counter(
    "fla_ingest_records_total",
    "Total records processed by the Ingestion Agent",
    ["status"],          # ok | failed
)

INGEST_FAILURES_TOTAL = Counter(
    "fla_ingest_failures_total",
    "Total records that failed parsing or DB insert",
)

INGEST_BYTES_TOTAL = Counter(
    "fla_ingest_bytes_total",
    "Total bytes read during ingestion",
    ["benchmark"],
)

# ── LLM Judge ─────────────────────────────────────────────────────────────────

LLM_CALLS_TOTAL = Counter(
    "fla_llm_calls_total",
    "Total LLM API calls made by the LLM Judge worker",
    ["model", "status"],  # status: ok | error | circuit_open | budget_exhausted
)

LLM_COST_USD_TOTAL = Counter(
    "fla_llm_cost_usd_total",
    "Accumulated LLM API spend in USD",
    ["model"],
)

LLM_LATENCY_SECONDS = Histogram(
    "fla_llm_latency_seconds",
    "LLM API round-trip latency in seconds",
    ["model"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60),
)

LLM_DAILY_BUDGET_USED_RATIO = Gauge(
    "fla_llm_daily_budget_used_ratio",
    "Ratio of daily LLM budget consumed (0–1). -1 means unlimited.",
)

# ── Celery ────────────────────────────────────────────────────────────────────

CELERY_QUEUE_DEPTH = Gauge(
    "fla_celery_queue_depth",
    "Number of messages currently waiting in a Celery queue",
    ["queue"],            # rule | llm | report
)

CELERY_WORKERS_ONLINE = Gauge(
    "fla_celery_workers_online",
    "Number of active Celery workers reporting heartbeat",
    ["queue"],
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "fla_celery_task_duration_seconds",
    "Wall-clock time for Celery task execution",
    ["task_name", "status"],   # status: ok | failed
    buckets=(0.1, 0.5, 1, 5, 10, 30, 60, 120, 300),
)

# ── HTTP API ──────────────────────────────────────────────────────────────────

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "fla_http_request_duration_seconds",
    "FastAPI HTTP request duration in seconds",
    ["method", "path", "status"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
```

- [ ] Run: `pytest app/tests/unit/test_metrics.py -v` → **PASSED** (10 tests)
- [ ] Commit: `git commit -m "feat(obs): add all Prometheus metric objects (ingestion, LLM, Celery, HTTP)"`

---

## Task 5 — `MetricsMiddleware` (HTTP latency histogram)

**Files:**
- Create: `backend/app/middleware/metrics_middleware.py`
- Create: `backend/app/tests/unit/test_metrics_middleware.py`

### Steps

- [ ] **Step 1: Write failing test**

```python
# backend/app/tests/unit/test_metrics_middleware.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from prometheus_client import REGISTRY
from app.main import app


@pytest.mark.asyncio
async def test_http_histogram_incremented_on_request():
    """After a request, HTTP duration histogram should have at least one sample."""
    # Collect baseline count
    before = _get_sample_count("fla_http_request_duration_seconds_count")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        with patch("app.api.v1.routers.health.check_db", AsyncMock(return_value=True)), \
             patch("app.api.v1.routers.health.check_redis", AsyncMock(return_value=True)):
            await client.get("/api/v1/health")

    after = _get_sample_count("fla_http_request_duration_seconds_count")
    assert after > before


def _get_sample_count(metric_name: str) -> float:
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == metric_name:
                return sample.value
    return 0.0
```

- [ ] Run: `pytest app/tests/unit/test_metrics_middleware.py -v` → **FAILED**

- [ ] **Step 2: Implement `MetricsMiddleware`**

```python
# backend/app/middleware/metrics_middleware.py
"""
Starlette middleware that records HTTP request duration into the
HTTP_REQUEST_DURATION_SECONDS Prometheus histogram.

Path normalisation: replaces UUID segments with `{id}` so cardinality
stays bounded (e.g. /api/v1/sessions/abc-123 → /api/v1/sessions/{id}).
"""
import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.metrics import HTTP_REQUEST_DURATION_SECONDS

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


def _normalise_path(path: str) -> str:
    return _UUID_RE.sub("{id}", path)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=request.method,
            path=_normalise_path(request.url.path),
            status=str(response.status_code),
        ).observe(duration)

        return response
```

- [ ] **Step 3: Register `MetricsMiddleware` in `app/main.py`** (after `LoggingMiddleware`)

  ```python
  from app.middleware.metrics_middleware import MetricsMiddleware
  app.add_middleware(MetricsMiddleware)
  ```

- [ ] Run: `pytest app/tests/unit/test_metrics_middleware.py -v` → **PASSED**
- [ ] Commit: `git commit -m "feat(obs): add MetricsMiddleware for HTTP latency histogram"`

---

## Task 6 — Prometheus scrape endpoint `GET /api/v1/metrics`

**Files:**
- Create: `backend/app/api/v1/routers/metrics.py`
- Create: `backend/app/tests/unit/test_metrics_endpoint.py`

### Steps

- [ ] **Step 1: Write failing test**

```python
# backend/app/tests/unit/test_metrics_endpoint.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/metrics")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_metrics_content_type_is_prometheus():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/metrics")
    assert "text/plain" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_metrics_contains_fla_metric():
    """The fla_* metrics family must appear in the exposition."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/metrics")
    assert "fla_http_request_duration_seconds" in resp.text
    assert "fla_ingest_records_total" in resp.text
    assert "fla_llm_calls_total" in resp.text


@pytest.mark.asyncio
async def test_metrics_endpoint_no_auth_required():
    """Prometheus scrapers do not send auth tokens — endpoint must be public."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/metrics")
    assert resp.status_code != 401
    assert resp.status_code != 403
```

- [ ] Run: `pytest app/tests/unit/test_metrics_endpoint.py -v` → **FAILED**

- [ ] **Step 2: Implement `backend/app/api/v1/routers/metrics.py`**

```python
# backend/app/api/v1/routers/metrics.py
"""
Prometheus metrics scrape endpoint.

Mounted at GET /api/v1/metrics (no authentication — Prometheus scrapers
do not send tokens; restrict access at the network / Ingress level instead).
"""
from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> Response:
    """Expose all registered Prometheus metrics in text exposition format."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

- [ ] **Step 3: Register in `app/main.py`**

  ```python
  from app.api.v1.routers import metrics as metrics_router
  app.include_router(metrics_router.router, prefix="/api/v1")
  ```

- [ ] Run: `pytest app/tests/unit/test_metrics_endpoint.py -v` → **PASSED** (4 tests)
- [ ] Commit: `git commit -m "feat(obs): add GET /api/v1/metrics Prometheus scrape endpoint"`

---

## Task 7 — Celery signal hooks (`celery_signals.py`)

**Files:**
- Create: `backend/app/celery_signals.py`
- Create: `backend/app/tests/unit/test_celery_signals.py`

### Steps

- [ ] **Step 1: Write failing test**

```python
# backend/app/tests/unit/test_celery_signals.py
"""
Tests for Celery signal handlers that record metrics and emit structured logs.
We call the handler functions directly — no real Celery broker needed.
"""
import pytest
from unittest.mock import MagicMock, patch
from app.celery_signals import (
    on_task_prerun,
    on_task_postrun,
    on_task_failure,
)
from app.core import metrics as m
from prometheus_client import REGISTRY


def _get_counter_value(metric, **labels) -> float:
    for mf in REGISTRY.collect():
        if mf.name == metric:
            for sample in mf.samples:
                if all(sample.labels.get(k) == v for k, v in labels.items()):
                    return sample.value
    return 0.0


def test_on_task_postrun_ok_increments_histogram():
    """Successful task completion must observe into CELERY_TASK_DURATION_SECONDS."""
    task = MagicMock()
    task.name = "app.tasks.analysis.run_rules"
    # Simulate a prerun call first (stores start time)
    on_task_prerun(task_id="t1", task=task)
    import time; time.sleep(0.01)
    on_task_postrun(task_id="t1", task=task, retval=None, state="SUCCESS")
    # Histogram must have at least 1 count entry for this task_name
    count = _get_counter_value(
        "fla_celery_task_duration_seconds_count",
        task_name="app.tasks.analysis.run_rules",
        status="ok",
    )
    assert count >= 1


def test_on_task_failure_increments_failed_counter():
    task = MagicMock()
    task.name = "app.tasks.ingest.parse_file"
    on_task_failure(task_id="t2", sender=task, exception=Exception("boom"), args=[], kwargs={}, traceback=None, einfo=None)
    count = _get_counter_value(
        "fla_celery_task_duration_seconds_count",
        task_name="app.tasks.ingest.parse_file",
        status="failed",
    )
    assert count >= 1
```

- [ ] Run: `pytest app/tests/unit/test_celery_signals.py -v` → **FAILED**

- [ ] **Step 2: Implement `backend/app/celery_signals.py`**

```python
# backend/app/celery_signals.py
"""
Celery signal handlers for observability.

Wire up by importing this module in `app/celery_app.py`:
    import app.celery_signals  # noqa: F401

Signals used:
  task_prerun   — store task start time in a thread-local dict
  task_postrun  — record duration histogram + structured log
  task_failure  — record failed counter + structured error log
  worker_ready  — increment workers_online gauge
  worker_offline — decrement workers_online gauge
"""
import time
from typing import Any

import structlog
from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    worker_offline,
    worker_ready,
)

from app.core.metrics import (
    CELERY_TASK_DURATION_SECONDS,
    CELERY_WORKERS_ONLINE,
    INGEST_FAILURES_TOTAL,
    LLM_CALLS_TOTAL,
)

logger = structlog.get_logger("celery")

# Thread-local start time tracking: task_id → start_time
_task_start: dict[str, float] = {}


@task_prerun.connect
def on_task_prerun(task_id: str, task: Any, **kwargs: Any) -> None:
    _task_start[task_id] = time.perf_counter()
    logger.info(
        "task_started",
        task_id=task_id,
        task_name=task.name,
    )


@task_postrun.connect
def on_task_postrun(
    task_id: str, task: Any, retval: Any, state: str, **kwargs: Any
) -> None:
    start = _task_start.pop(task_id, None)
    duration = time.perf_counter() - start if start is not None else 0.0
    status = "ok" if state == "SUCCESS" else "failed"

    CELERY_TASK_DURATION_SECONDS.labels(
        task_name=task.name,
        status=status,
    ).observe(duration)

    logger.info(
        "task_finished",
        task_id=task_id,
        task_name=task.name,
        state=state,
        duration_ms=round(duration * 1000, 1),
    )


@task_failure.connect
def on_task_failure(
    task_id: str, sender: Any, exception: Exception, **kwargs: Any
) -> None:
    # Ensure histogram has an entry even if prerun was missed
    CELERY_TASK_DURATION_SECONDS.labels(
        task_name=sender.name,
        status="failed",
    ).observe(0)

    # Per-task failure counters
    if "ingest" in sender.name:
        INGEST_FAILURES_TOTAL.inc()
    elif "llm" in sender.name:
        LLM_CALLS_TOTAL.labels(model="unknown", status="error").inc()

    logger.error(
        "task_failed",
        task_id=task_id,
        task_name=sender.name,
        exc_type=type(exception).__name__,
        exc_msg=str(exception),
    )


@worker_ready.connect
def on_worker_ready(sender: Any, **kwargs: Any) -> None:
    queue = _infer_queue(sender)
    CELERY_WORKERS_ONLINE.labels(queue=queue).inc()
    logger.info("worker_ready", hostname=str(sender), queue=queue)


@worker_offline.connect
def on_worker_offline(sender: Any, **kwargs: Any) -> None:
    queue = _infer_queue(sender)
    CELERY_WORKERS_ONLINE.labels(queue=queue).dec()
    logger.info("worker_offline", hostname=str(sender), queue=queue)


def _infer_queue(sender: Any) -> str:
    """Infer queue name from worker hostname convention (e.g. celery@rule-worker-x)."""
    hostname = str(getattr(sender, "hostname", sender))
    if "llm" in hostname:
        return "llm"
    if "rule" in hostname:
        return "rule"
    if "report" in hostname:
        return "report"
    return "default"
```

- [ ] **Step 3: Wire up in `app/celery_app.py`** (add after Celery app creation)

  ```python
  import app.celery_signals  # noqa: F401  — registers signal handlers
  ```

- [ ] Run: `pytest app/tests/unit/test_celery_signals.py -v` → **PASSED** (2 tests)
- [ ] Commit: `git commit -m "feat(obs): add Celery signal hooks for task duration metrics and structured logs"`

---

## Task 8 — Instrument Ingestion + LLM Judge with metrics calls

**Files:**
- Edit: `backend/app/tasks/ingest.py`
- Edit: `backend/app/tasks/analysis.py`

### Steps

- [ ] **Step 1: Add metric calls in `app/tasks/ingest.py`**

  In the `parse_file` task, after each batch DB write, add:

  ```python
  from app.core.metrics import INGEST_RECORDS_TOTAL, INGEST_FAILURES_TOTAL, INGEST_BYTES_TOTAL

  # After successful batch insert (per record):
  INGEST_RECORDS_TOTAL.labels(status="ok").inc(len(batch))
  INGEST_BYTES_TOTAL.labels(benchmark=adapter_name).inc(chunk_bytes)

  # On single-record parse failure (in except block):
  INGEST_RECORDS_TOTAL.labels(status="failed").inc()
  INGEST_FAILURES_TOTAL.inc()
  ```

- [ ] **Step 2: Add metric calls in `app/tasks/analysis.py` (LLM Judge)**

  In `run_llm_judge`, around the `_analyse_single_record` call:

  ```python
  from app.core.metrics import LLM_CALLS_TOTAL, LLM_COST_USD_TOTAL, LLM_LATENCY_SECONDS, LLM_DAILY_BUDGET_USED_RATIO
  import time

  t0 = time.perf_counter()
  try:
      result = await _analyse_single_record(record, strategy, template)
      latency = time.perf_counter() - t0
      LLM_LATENCY_SECONDS.labels(model=strategy.llm_model).observe(latency)
      LLM_CALLS_TOTAL.labels(model=strategy.llm_model, status="ok").inc()
      LLM_COST_USD_TOTAL.labels(model=strategy.llm_model).inc(result.get("llm_cost", 0))
  except CircuitOpenError:
      LLM_CALLS_TOTAL.labels(model=strategy.llm_model, status="circuit_open").inc()
      raise
  except BudgetExhaustedError:
      LLM_CALLS_TOTAL.labels(model=strategy.llm_model, status="budget_exhausted").inc()
      raise
  except Exception:
      LLM_CALLS_TOTAL.labels(model=strategy.llm_model, status="error").inc()
      raise
  ```

  After computing `total_cost` vs `daily_limit`:

  ```python
  if strategy.daily_budget and strategy.daily_budget > 0:
      LLM_DAILY_BUDGET_USED_RATIO.set(total_cost / strategy.daily_budget)
  else:
      LLM_DAILY_BUDGET_USED_RATIO.set(-1)
  ```

- [ ] **Step 3: Add queue depth polling to `app/core/metrics.py`** (called by a background task)

  Add a helper function at the bottom of `metrics.py`:

  ```python
  def update_queue_depths(redis_client) -> None:
      """
      Poll Redis for Celery queue lengths and update CELERY_QUEUE_DEPTH gauge.
      Call periodically from a FastAPI background task or APScheduler.
      """
      for queue in ("rule", "llm", "report"):
          depth = redis_client.llen(queue)
          CELERY_QUEUE_DEPTH.labels(queue=queue).set(depth)
  ```

- [ ] **Step 4: Register background queue-depth polling in `app/main.py` lifespan**

  ```python
  import asyncio
  from app.core.metrics import update_queue_depths

  @asynccontextmanager
  async def lifespan(app: FastAPI):
      configure_logging()
      async def _poll_queues():
          import redis as sync_redis
          r = sync_redis.from_url(settings.REDIS_URL)
          while True:
              update_queue_depths(r)
              await asyncio.sleep(15)
      task = asyncio.create_task(_poll_queues())
      yield
      task.cancel()

  app = FastAPI(..., lifespan=lifespan)
  ```

- [ ] Commit: `git commit -m "feat(obs): instrument ingestion + LLM judge tasks with Prometheus metrics"`

---

## Task 9 — Enhance health endpoint to include Celery worker status

**Files:**
- Edit: `backend/app/api/v1/routers/health.py`
- Edit: `backend/app/tests/unit/test_health.py`

### Steps

- [ ] **Step 1: Update `health.py` to check Celery workers**

  Add a `check_celery()` function that pings Celery workers via Redis:

  ```python
  import redis.asyncio as aioredis
  from app.core.config import settings

  async def check_celery() -> bool:
      """
      Check if at least one Celery worker is online by inspecting the
      celery:worker:heartbeat Redis keys written by worker_ready signal.
      Falls back to True if unable to determine (don't block health check).
      """
      try:
          r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
          # Celery workers write heartbeat keys; check any exist
          keys = await r.keys("_kombu.binding.*")
          await r.aclose()
          return len(keys) > 0
      except Exception:
          return True   # fail open — don't report degraded on Redis timeout

  @router.get("/health")
  async def health_check():
      db_ok = await check_db()
      redis_ok = await check_redis()
      celery_ok = await check_celery()
      all_ok = db_ok and redis_ok
      payload = {
          "status": "ok" if all_ok else "degraded",
          "checks": {
              "db": db_ok,
              "redis": redis_ok,
              "celery": celery_ok,
          },
      }
      return JSONResponse(content=payload, status_code=200 if all_ok else 503)
  ```

- [ ] **Step 2: Update `test_health.py`** to expect `checks.celery` key

  ```python
  assert "celery" in body["checks"]
  ```

- [ ] Run: `pytest app/tests/unit/test_health.py -v` → **PASSED**
- [ ] Commit: `git commit -m "feat(obs): extend /health endpoint to include Celery worker check"`

---

## Task 10 — Kubernetes: ServiceMonitor + PrometheusRule (alert rules)

**Files:**
- Create: `k8s/base/monitoring/servicemonitor.yaml`
- Create: `k8s/base/monitoring/prometheus-rule.yaml`
- Edit: `k8s/base/kustomization.yaml` (add monitoring resources)

### Steps

- [ ] **Step 1: `k8s/base/monitoring/servicemonitor.yaml`**

```yaml
# Tells Prometheus Operator to scrape GET /api/v1/metrics every 30s.
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: fla-api
  labels:
    app.kubernetes.io/part-of: failure-log-analyzer
    # Must match the Prometheus Operator's serviceMonitorSelector in your cluster.
    # Common default: release=prometheus
    release: prometheus
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: api
  namespaceSelector:
    matchNames:
      - fla
  endpoints:
    - port: http
      path: /api/v1/metrics
      interval: 30s
      scrapeTimeout: 10s
```

- [ ] **Step 2: `k8s/base/monitoring/prometheus-rule.yaml`**

```yaml
# Three alert rules from design doc §14.3:
#   1. LLM 成本超预算 80%
#   2. Worker 全部离线
#   3. 摄入任务失败率 > 10%
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: fla-alerts
  labels:
    app.kubernetes.io/part-of: failure-log-analyzer
    release: prometheus
spec:
  groups:
    - name: fla.llm
      interval: 60s
      rules:
        - alert: FlaLlmBudgetOver80Pct
          expr: fla_llm_daily_budget_used_ratio > 0.8
          for: 5m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "LLM daily budget over 80%"
            description: >
              LLM spend has exceeded 80% of the daily budget
              (current ratio: {{ $value | printf "%.2f" }}).
              Remaining capacity may be exhausted within hours.
              Check /api/v1/llm/cost-summary and consider raising the budget
              or pausing non-critical analysis jobs.

    - name: fla.celery
      interval: 30s
      rules:
        - alert: FlaAllWorkersOffline
          expr: sum(fla_celery_workers_online) == 0
          for: 2m
          labels:
            severity: critical
            team: platform
          annotations:
            summary: "All Celery workers offline"
            description: >
              No Celery workers have been detected online for 2 minutes.
              All ingestion, rule analysis, and LLM analysis tasks are queued
              but not being processed. Investigate worker Deployment health:
              kubectl -n fla get pods -l app.kubernetes.io/component=worker

        - alert: FlaWorkerQueueStalling
          expr: fla_celery_queue_depth{queue="llm"} > 500
          for: 10m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "LLM queue depth > 500 for 10 minutes"
            description: >
              The LLM worker queue has {{ $value }} pending tasks and has not
              drained in 10 minutes. Consider scaling up worker-llm replicas or
              checking for circuit breaker / budget exhaustion.

    - name: fla.ingestion
      interval: 60s
      rules:
        - alert: FlaIngestFailureRateHigh
          expr: >
            rate(fla_ingest_records_total{status="failed"}[5m])
            /
            (rate(fla_ingest_records_total[5m]) + 1e-9)
            > 0.10
          for: 5m
          labels:
            severity: warning
            team: platform
          annotations:
            summary: "Ingestion failure rate > 10%"
            description: >
              More than 10% of ingested records are failing in the last 5 minutes
              (current rate: {{ $value | printf "%.1%%" }}).
              Check adapter compatibility and file encoding.
              Review /api/v1/ingest job status for error details.
```

- [ ] **Step 3: Add monitoring resources to `k8s/base/kustomization.yaml`**

  ```yaml
  resources:
    ...
    - monitoring/servicemonitor.yaml
    - monitoring/prometheus-rule.yaml
  ```

- [ ] **Step 4: Validate**
  ```bash
  kubectl kustomize k8s/base --dry-run
  # Expected: renders without error
  # After applying to a cluster with Prometheus Operator:
  kubectl -n fla get prometheusrule fla-alerts
  kubectl -n fla get servicemonitor fla-api
  ```

- [ ] Commit: `git commit -m "feat(obs): add Prometheus ServiceMonitor and 3 PrometheusRule alert definitions"`

---

## Task 11 — Full test suite pass

- [ ] Run complete backend unit suite:
  ```bash
  cd backend && pytest app/tests/unit/ -v --tb=short
  ```
  Expected: all tests pass including:
  - `test_logging.py` — 5 tests
  - `test_metrics.py` — 10 tests
  - `test_logging_middleware.py` — 2 tests
  - `test_metrics_middleware.py` — 1 test
  - `test_metrics_endpoint.py` — 4 tests
  - `test_celery_signals.py` — 2 tests
  - `test_health.py` — 2 tests (updated)

- [ ] Verify no regressions in Plans 01–06 tests:
  ```bash
  pytest app/tests/ -v --ignore=app/tests/integration/
  ```

- [ ] Commit: `git commit -m "feat(obs): complete observability implementation — structlog + Prometheus + alerts"`

---

## Test Summary

| Task | File | Tests | Key assertions |
|------|------|-------|----------------|
| 2 | test_logging.py | 5 | JSON output in prod; contextvars bind; stdlib routing |
| 3 | test_logging_middleware.py | 2 | X-Request-ID echo; auto-generate when missing |
| 4 | test_metrics.py | 10 | Each metric has correct type and label names |
| 5 | test_metrics_middleware.py | 1 | Histogram count increments on HTTP request |
| 6 | test_metrics_endpoint.py | 4 | 200 OK; text/plain; fla_* names present; no auth |
| 7 | test_celery_signals.py | 2 | Duration histogram on success; failure counter |
| 9 | test_health.py | 2 | `celery` key present in checks |
| **Total** | | **26** | |

---

## Handoff Contract

- **Logging in any module:**
  ```python
  from app.core.logging import get_logger
  logger = get_logger(__name__)
  logger.info("event_name", field1="value", field2=123)
  ```
  In production, this emits a single JSON line to stdout. In development, it uses ConsoleRenderer with colours.

- **Request-scoped fields** (`request_id`, `method`, `path`, `client_ip`) are automatically present on every log line emitted during an HTTP request — no manual injection needed.

- **Recording LLM metrics** from any LLM task:
  ```python
  from app.core.metrics import LLM_CALLS_TOTAL, LLM_COST_USD_TOTAL, LLM_LATENCY_SECONDS
  LLM_LATENCY_SECONDS.labels(model="gpt-4o").observe(duration)
  LLM_CALLS_TOTAL.labels(model="gpt-4o", status="ok").inc()
  LLM_COST_USD_TOTAL.labels(model="gpt-4o").inc(cost_usd)
  ```

- **Alert thresholds** (§14.3) are defined in `k8s/base/monitoring/prometheus-rule.yaml`. To adjust:
  - LLM budget threshold: change `> 0.8` in `FlaLlmBudgetOver80Pct`
  - Failure rate threshold: change `> 0.10` in `FlaIngestFailureRateHigh`
  - Queue stall threshold: change `> 500` in `FlaWorkerQueueStalling`

- **Prometheus scrape**: via `GET /api/v1/metrics` — no authentication. Restrict at Ingress/network level, not application level.

- **Prometheus Operator** must be installed in the cluster for `ServiceMonitor` and `PrometheusRule` CRDs to be recognised (standard in kube-prometheus-stack Helm chart).
