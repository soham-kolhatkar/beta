"""Shared async Redis client lifecycle (Phase 7: rate limiting).

`_client` is a plain module global rather than something imported by name
elsewhere (`from app.core.redis import _client` would capture `None`
forever, since `init()` reassigns the name after other modules have already
imported it) — callers must go through `get_client()` so they always see
the current value.
"""

import redis.asyncio as redis

from app.core.config import settings

_client: redis.Redis | None = None


async def init() -> redis.Redis:
    global _client
    _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_client() -> redis.Redis | None:
    """`None` when Redis hasn't been initialized (e.g. tests, where the
    app's lifespan never runs — see conftest.py) or hasn't started yet.
    Callers that can degrade gracefully (the auth email lockout) should
    treat `None` as "skip"; callers that can't (fastapi-limiter's
    `RateLimiter`) are expected to be overridden to no-ops in tests instead.
    """
    return _client
