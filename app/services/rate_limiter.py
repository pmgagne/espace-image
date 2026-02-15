import asyncio
import time
from collections import deque


class RateLimiter:
    """
    Simple async in-memory sliding-window rate limiter.

    Usage:
        await rate_limiter.acquire("geocoding", max_calls=5, period=60)

    Example:
        allowed = await rate_limiter.acquire("geocoding:open-meteo", max_calls=6, period=60)
        if not allowed:
            logger.warning("Rate limit exceeded for geocoding: %s", query)
            return None

    This is intentionally lightweight and not suitable for multi-process
    deployments. It prevents bursts during local dev and reduces accidental
    abuse of upstream geocoding services.
    """

    def __init__(self) -> None:
        """
        Initialize the RateLimiter with empty buckets and locks.
        """
        self._buckets: dict[str, deque[float]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, key: str) -> asyncio.Lock:
        """
        Get or create an asyncio.Lock for a given key.

        Args:
            key (str): The rate limit key.

        Returns:
            asyncio.Lock: The lock for the key.
        """
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def acquire(self, key: str, max_calls: int = 5, period: int = 60) -> bool:
        """
        Attempt to acquire a slot for `key`.

        Args:
            key (str): The rate limit key.
            max_calls (int): Maximum allowed calls in the period.
            period (int): Time window in seconds.

        Returns:
            bool: True if within rate limits, False otherwise.
        """
        now = time.monotonic()
        lock = self._get_lock(key)
        async with lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = deque()
                self._buckets[key] = bucket

            # Purge old timestamps
            cutoff = now - period
            while bucket and bucket[0] < cutoff:
                bucket.popleft()

            if len(bucket) < max_calls:
                bucket.append(now)
                return True

            return False


# Module-level singleton for convenience and explicit typing
rate_limiter: RateLimiter = RateLimiter()
