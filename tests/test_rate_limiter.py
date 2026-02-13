import asyncio

from app.services.rate_limiter import RateLimiter


def test_rate_limiter_allows_and_blocks():
    rl = RateLimiter()
    loop = asyncio.new_event_loop()
    try:
        # allow one call per second
        allowed = loop.run_until_complete(rl.acquire("testkey", max_calls=1, period=1))
        assert allowed is True

        # immediate second call should be blocked
        allowed2 = loop.run_until_complete(rl.acquire("testkey", max_calls=1, period=1))
        assert allowed2 is False
    finally:
        loop.close()


def test_rate_limiter_resets_after_period():
    rl = RateLimiter()
    loop = asyncio.new_event_loop()
    try:
        allowed = loop.run_until_complete(rl.acquire("resetkey", max_calls=1, period=1))
        assert allowed is True
        # wait longer than period
        loop.run_until_complete(asyncio.sleep(1.1))
        allowed2 = loop.run_until_complete(rl.acquire("resetkey", max_calls=1, period=1))
        assert allowed2 is True
    finally:
        loop.close()
