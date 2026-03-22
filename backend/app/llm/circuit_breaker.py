"""Simple circuit breaker for provider-call protection."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal


CircuitState = Literal["closed", "open", "half_open"]


@dataclass
class CircuitBreaker:
    """Track transient failures and stop traffic when a provider is unhealthy."""

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        self.failure_threshold = max(1, int(self.failure_threshold))
        self.recovery_timeout_seconds = max(0.0, float(self.recovery_timeout_seconds))
        self._state: CircuitState = "closed"
        self._consecutive_failures = 0
        self._opened_at_monotonic: float | None = None

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def consecutive_failures(self) -> int:
        return self._consecutive_failures

    def can_execute(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "half_open":
            return True

        # open state
        if self._opened_at_monotonic is None:
            return False

        now = time.monotonic()
        if now - self._opened_at_monotonic >= self.recovery_timeout_seconds:
            self._state = "half_open"
            return True
        return False

    def record_success(self) -> None:
        self._state = "closed"
        self._consecutive_failures = 0
        self._opened_at_monotonic = None

    def record_failure(self) -> None:
        if self._state == "half_open":
            self._state = "open"
            self._opened_at_monotonic = time.monotonic()
            self._consecutive_failures = self.failure_threshold
            return

        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._state = "open"
            self._opened_at_monotonic = time.monotonic()
