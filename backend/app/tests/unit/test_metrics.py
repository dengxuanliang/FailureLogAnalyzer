from prometheus_client import Counter, Gauge, Histogram
from unittest.mock import MagicMock, call

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


def test_update_queue_depths_polls_all_expected_queues() -> None:
    redis = MagicMock()
    redis.llen.side_effect = [1, 2, 3, 4]
    gauge = MagicMock()

    original = m.CELERY_QUEUE_DEPTH
    try:
        m.CELERY_QUEUE_DEPTH = gauge
        m.update_queue_depths(redis)
    finally:
        m.CELERY_QUEUE_DEPTH = original

    assert redis.llen.call_args_list == [
        call("celery"),
        call("rule"),
        call("llm"),
        call("report"),
    ]
    assert gauge.labels.call_args_list == [
        call(queue="celery"),
        call(queue="rule"),
        call(queue="llm"),
        call(queue="report"),
    ]
