import asyncio
import time
from collections import defaultdict, deque
from typing import Dict

from loguru import logger


class AsyncRateLimiter:
    """Sliding-window token-bucket rate limiter, keyed per domain."""

    def __init__(self, requests_per_window: int, window_seconds: int):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._domain_queues: Dict[str, deque] = defaultdict(deque)
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, domain: str) -> None:
        async with self._locks[domain]:
            now = time.monotonic()
            queue = self._domain_queues[domain]

            # Drop timestamps outside the current window
            cutoff = now - self.window_seconds
            while queue and queue[0] < cutoff:
                queue.popleft()

            if len(queue) >= self.requests_per_window:
                wait_for = queue[0] + self.window_seconds - now
                if wait_for > 0:
                    logger.debug(f"Rate-limiting {domain}: sleeping {wait_for:.2f}s")
                    await asyncio.sleep(wait_for)
                    # Re-prune after sleep
                    cutoff = time.monotonic() - self.window_seconds
                    while queue and queue[0] < cutoff:
                        queue.popleft()

            queue.append(time.monotonic())

    def domain_stats(self, domain: str) -> Dict:
        now = time.monotonic()
        recent = [t for t in self._domain_queues[domain] if t >= now - self.window_seconds]
        return {
            "domain": domain,
            "requests_in_window": len(recent),
            "limit": self.requests_per_window,
            "window_seconds": self.window_seconds,
        }
