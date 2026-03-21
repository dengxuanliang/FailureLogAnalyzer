import pytest

from app.llm.rate_limiter import AsyncRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_waits_for_interval(monkeypatch):
    timeline = {"value": 10.0}
    slept: list[float] = []

    monkeypatch.setattr("app.llm.rate_limiter.time.monotonic", lambda: timeline["value"])

    async def _sleep(seconds: float) -> None:
        slept.append(seconds)
        timeline["value"] += seconds

    limiter = AsyncRateLimiter(requests_per_second=2.0, sleep_func=_sleep)

    await limiter.acquire()
    await limiter.acquire()

    assert slept
    assert slept[0] == pytest.approx(0.5, abs=1e-3)


@pytest.mark.asyncio
async def test_rate_limiter_noop_when_disabled():
    limiter = AsyncRateLimiter(requests_per_second=None)
    await limiter.acquire()
    await limiter.acquire()
