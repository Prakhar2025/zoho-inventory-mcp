"""Client-side pacing and retry timing.

Zoho's free plan allows 1,000 API calls per day and 5 concurrent requests.
The connector therefore calls strictly serially with a minimum spacing between
calls, and treats any server-side 429 as a signal to back off, honoring the
Retry-After header when Zoho sends one.

Delays use exponential backoff with jitter so parallel processes do not
synchronize into a thundering herd.
"""

from __future__ import annotations

import asyncio
import random


class RateLimiter:
    """Serial call pacing plus retry backoff policy."""

    def __init__(
        self,
        min_interval: float = 0.5,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        if min_interval < 0:
            raise ValueError("min_interval must be >= 0")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self._min_interval = min_interval
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._next_slot = 0.0

    @property
    def max_retries(self) -> int:
        return self._max_retries

    async def acquire(self) -> None:
        """Reserve the next call slot, sleeping if calls arrive too fast."""
        loop = asyncio.get_running_loop()
        now = loop.time()
        wait = self._next_slot - now
        if wait > 0:
            await self._sleep(wait)
            now = loop.time()
        self._next_slot = max(now, self._next_slot) + self._min_interval

    async def backoff(self, attempt: int, retry_after: float | None = None) -> None:
        """Wait before retrying after a throttled or failed attempt.

        `attempt` is zero-based. An explicit Retry-After value always wins and
        is capped at max_delay.
        """
        if retry_after is not None:
            delay = min(max(retry_after, 0.0), self._max_delay)
        else:
            exponential = self._base_delay * (2**attempt)
            delay = min(exponential + random.uniform(0, exponential * 0.25), self._max_delay)
        await self._sleep(delay)

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
