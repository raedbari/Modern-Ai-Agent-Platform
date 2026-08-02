"""Redis-backed fixed-window rate limiting shared by API entry points."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Protocol

from fastapi import Depends

from backend.app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class RateLimiter(Protocol):
    async def check(
        self,
        *,
        bucket: str,
        identity: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult: ...


class DisabledRateLimiter:
    """Development/test fallback used only when no Redis URL is configured."""

    async def check(
        self,
        *,
        bucket: str,
        identity: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        del bucket, identity
        return RateLimitResult(
            allowed=True,
            remaining=limit,
            retry_after_seconds=window_seconds,
        )


class RedisRateLimiter:
    """Atomic fixed-window limiter using one Redis Lua operation."""

    _SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""

    def __init__(self, redis_url: str, *, key_prefix: str = "maap:rate"):
        from redis.asyncio import Redis

        self._redis = Redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        self._key_prefix = key_prefix

    async def check(
        self,
        *,
        bucket: str,
        identity: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("Rate-limit values must be positive.")

        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        key = f"{self._key_prefix}:{bucket}:{digest}"
        current, ttl = await self._redis.eval(
            self._SCRIPT,
            1,
            key,
            window_seconds,
        )
        count = int(current)
        retry_after = max(int(ttl), 1)
        return RateLimitResult(
            allowed=count <= limit,
            remaining=max(limit - count, 0),
            retry_after_seconds=retry_after,
        )


_DISABLED_LIMITER = DisabledRateLimiter()


@lru_cache(maxsize=8)
def _redis_limiter(redis_url: str) -> RedisRateLimiter:
    return RedisRateLimiter(redis_url)


def get_rate_limiter(
    settings: Annotated[Settings, Depends(get_settings)],
) -> RateLimiter:
    if settings.redis_url is None:
        return _DISABLED_LIMITER
    redis_url = settings.redis_url.get_secret_value().strip()
    if not redis_url:
        return _DISABLED_LIMITER
    return _redis_limiter(redis_url)
