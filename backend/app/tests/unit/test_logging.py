import json
import logging

import pytest
import structlog

from app.core.config import settings
from app.core.logging import configure_logging, get_logger


def _last_stdout_line(capsys: pytest.CaptureFixture[str]) -> str:
    output = capsys.readouterr().out.strip().splitlines()
    return output[-1] if output else ""


def test_configure_logging_dev_mode_uses_console_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    configure_logging()

    processors = structlog.get_config().get("processors", [])
    assert processors
    assert type(processors[-1]).__name__ == "ConsoleRenderer"


def test_configure_logging_prod_mode_outputs_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "LOG_LEVEL", "INFO", raising=False)

    configure_logging()
    logger = get_logger("test.prod")
    logger.info("hello", key="value")

    line = _last_stdout_line(capsys)
    parsed = json.loads(line)

    assert parsed["event"] == "hello"
    assert parsed["key"] == "value"
    assert parsed["level"] == "info"
    assert "timestamp" in parsed


def test_get_logger_returns_bound_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    configure_logging()

    logger = get_logger("test.module")
    assert logger is not None
    logger.info("test message", request_id="abc-123", user_id="u1")


def test_context_var_binding_included_in_log(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    configure_logging()

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id="req-xyz")

    logger = get_logger("test.ctx")
    logger.info("bound context test")

    parsed = json.loads(_last_stdout_line(capsys))
    assert parsed["request_id"] == "req-xyz"

    structlog.contextvars.clear_contextvars()


def test_stdlib_logging_routed_through_structlog(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    configure_logging()

    stdlib_logger = logging.getLogger("uvicorn.error")
    stdlib_logger.info("stdlib message")

    assert logging.getLogger("uvicorn").handlers == []
    assert logging.getLogger("uvicorn.access").handlers == []
