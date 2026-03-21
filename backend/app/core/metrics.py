"""Prometheus metric objects for FailureLogAnalyzer."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

INGEST_RECORDS_TOTAL = Counter(
    "fla_ingest_records_total",
    "Total records processed by ingestion",
    ["status"],
)

INGEST_FAILURES_TOTAL = Counter(
    "fla_ingest_failures_total",
    "Total records failed during ingestion",
)

INGEST_BYTES_TOTAL = Counter(
    "fla_ingest_bytes_total",
    "Total bytes read during ingestion",
    ["benchmark"],
)

LLM_CALLS_TOTAL = Counter(
    "fla_llm_calls_total",
    "Total LLM API calls",
    ["model", "status"],
)

LLM_COST_USD_TOTAL = Counter(
    "fla_llm_cost_usd_total",
    "Accumulated LLM cost in USD",
    ["model"],
)

LLM_LATENCY_SECONDS = Histogram(
    "fla_llm_latency_seconds",
    "LLM API latency in seconds",
    ["model"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60),
)

LLM_DAILY_BUDGET_USED_RATIO = Gauge(
    "fla_llm_daily_budget_used_ratio",
    "Current fraction of daily LLM budget used",
)

CELERY_QUEUE_DEPTH = Gauge(
    "fla_celery_queue_depth",
    "Pending messages in Celery queues",
    ["queue"],
)

CELERY_WORKERS_ONLINE = Gauge(
    "fla_celery_workers_online",
    "Online Celery worker count",
    ["queue"],
)

CELERY_TASK_DURATION_SECONDS = Histogram(
    "fla_celery_task_duration_seconds",
    "Celery task wall-clock duration in seconds",
    ["task_name", "status"],
    buckets=(0.1, 0.5, 1, 5, 10, 30, 60, 120, 300),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "fla_http_request_duration_seconds",
    "FastAPI request duration in seconds",
    ["method", "path", "status"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)


def update_queue_depths(redis_client) -> None:
    """Poll Redis queue lengths and update queue-depth gauge."""
    for queue in ("rule", "llm", "report"):
        depth = redis_client.llen(queue)
        CELERY_QUEUE_DEPTH.labels(queue=queue).set(depth)
