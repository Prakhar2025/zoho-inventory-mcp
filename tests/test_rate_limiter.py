"""RateLimiter: spacing between calls and retry backoff policy."""

import time

from zoho_inventory_mcp.rate_limiter import RateLimiter


async def test_acquire_enforces_minimum_spacing():
    limiter = RateLimiter(min_interval=0.05)
    await limiter.acquire()

    started = time.perf_counter()
    await limiter.acquire()
    elapsed = time.perf_counter() - started

    assert elapsed >= 0.04


async def test_acquire_does_not_wait_on_first_call():
    limiter = RateLimiter(min_interval=1.0)
    started = time.perf_counter()
    await limiter.acquire()

    assert time.perf_counter() - started < 0.5


async def test_backoff_honors_retry_after_and_caps_it():
    limiter = RateLimiter(max_delay=5.0)
    seen: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        seen.append(seconds)

    limiter._sleep = fake_sleep
    await limiter.backoff(2, retry_after=7.0)

    assert seen == [5.0]


async def test_backoff_grows_exponentially_with_jitter():
    limiter = RateLimiter(base_delay=1.0, max_delay=100.0)
    seen: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        seen.append(seconds)

    limiter._sleep = fake_sleep
    for attempt in range(4):
        await limiter.backoff(attempt)

    for attempt, delay in enumerate(seen):
        floor = 1.0 * 2**attempt
        ceiling = floor * 1.25 + 1e-9
        assert floor <= delay <= ceiling
