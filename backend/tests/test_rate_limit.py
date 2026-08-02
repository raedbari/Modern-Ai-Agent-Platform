"""Tests for the shared Redis-backed rate limiter."""

from __future__ import annotations

import pytest

from backend.app.core.rate_limit import DisabledRateLimiter, RedisRateLimiter


@pytest.mark.asyncio
async def test_redis_rate_limiter_uses_atomic_script_and_hashed_identity() -> None:
    limiter = RedisRateLimiter("redis://127.0.0.1:6379/15")

    class FakeRedis:
        def __init__(self) -> None:
            self.args = None

        async def eval(self, *args):
            self.args = args
            return [6, 42]

    fake = FakeRedis()
    limiter._redis = fake
    result = await limiter.check(
        bucket="widget-chat-session",
        identity="sensitive-session-identifier",
        limit=5,
        window_seconds=60,
    )

    assert result.allowed is False
    assert result.remaining == 0
    assert result.retry_after_seconds == 42
    assert fake.args is not None
    redis_key = fake.args[2]
    assert redis_key.startswith("maap:rate:widget-chat-session:")
    assert "sensitive-session-identifier" not in redis_key


@pytest.mark.asyncio
async def test_disabled_rate_limiter_is_explicitly_permissive() -> None:
    result = await DisabledRateLimiter().check(
        bucket="test",
        identity="identity",
        limit=7,
        window_seconds=30,
    )
    assert result.allowed is True
    assert result.remaining == 7
