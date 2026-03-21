from app.llm.circuit_breaker import CircuitBreaker


def test_circuit_breaker_opens_after_threshold_and_recovers(monkeypatch):
    now = {"value": 100.0}

    monkeypatch.setattr("app.llm.circuit_breaker.time.monotonic", lambda: now["value"])

    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=10)

    assert breaker.state == "closed"
    assert breaker.can_execute() is True

    breaker.record_failure()
    assert breaker.state == "closed"
    assert breaker.can_execute() is True

    breaker.record_failure()
    assert breaker.state == "open"
    assert breaker.can_execute() is False

    now["value"] += 11
    assert breaker.can_execute() is True
    assert breaker.state == "half_open"

    breaker.record_success()
    assert breaker.state == "closed"
    assert breaker.can_execute() is True


def test_circuit_breaker_reopens_on_half_open_failure(monkeypatch):
    now = {"value": 50.0}
    monkeypatch.setattr("app.llm.circuit_breaker.time.monotonic", lambda: now["value"])

    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout_seconds=5)
    breaker.record_failure()
    assert breaker.can_execute() is False

    now["value"] += 6
    assert breaker.can_execute() is True
    assert breaker.state == "half_open"

    breaker.record_failure()
    assert breaker.state == "open"
    assert breaker.can_execute() is False
