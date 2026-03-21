from prometheus_client import Counter, Gauge, Histogram

from app.core import metrics as m


def test_ingest_records_total_is_counter() -> None:
    assert isinstance(m.INGEST_RECORDS_TOTAL, Counter)


def test_ingest_records_total_has_status_label() -> None:
    assert "status" in m.INGEST_RECORDS_TOTAL._labelnames


def test_llm_calls_total_is_counter() -> None:
    assert isinstance(m.LLM_CALLS_TOTAL, Counter)
    assert "model" in m.LLM_CALLS_TOTAL._labelnames
    assert "status" in m.LLM_CALLS_TOTAL._labelnames


def test_llm_cost_usd_total_is_counter() -> None:
    assert isinstance(m.LLM_COST_USD_TOTAL, Counter)
    assert "model" in m.LLM_COST_USD_TOTAL._labelnames


def test_llm_latency_seconds_is_histogram() -> None:
    assert isinstance(m.LLM_LATENCY_SECONDS, Histogram)
    assert "model" in m.LLM_LATENCY_SECONDS._labelnames


def test_celery_queue_depth_is_gauge() -> None:
    assert isinstance(m.CELERY_QUEUE_DEPTH, Gauge)
    assert "queue" in m.CELERY_QUEUE_DEPTH._labelnames


def test_http_request_duration_is_histogram() -> None:
    assert isinstance(m.HTTP_REQUEST_DURATION_SECONDS, Histogram)
    assert "method" in m.HTTP_REQUEST_DURATION_SECONDS._labelnames
    assert "path" in m.HTTP_REQUEST_DURATION_SECONDS._labelnames
    assert "status" in m.HTTP_REQUEST_DURATION_SECONDS._labelnames


def test_ingest_failures_total_is_counter() -> None:
    assert isinstance(m.INGEST_FAILURES_TOTAL, Counter)


def test_daily_budget_used_ratio_is_gauge() -> None:
    assert isinstance(m.LLM_DAILY_BUDGET_USED_RATIO, Gauge)


def test_workers_online_is_gauge() -> None:
    assert isinstance(m.CELERY_WORKERS_ONLINE, Gauge)
    assert "queue" in m.CELERY_WORKERS_ONLINE._labelnames
