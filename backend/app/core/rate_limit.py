"""Phase 7: per-IP rate limiting for docs/SECURITY.md §36's high-risk
endpoint groups, backed by Redis directly.

`fastapi-limiter` was tried first (matching the user's explicit choice of
"Redis + fastapi-limiter" over Arcjet) but turned out to be broken against
this project's FastAPI version: it inspects `request.app.routes` expecting
every entry to have a `.path` attribute, but FastAPI 0.141.1 wraps included
routers in an internal `_IncludedRouter` object that has none, so it threw
`AttributeError` on the very first request through any rate-limited route
in both its published API generations (0.1.6 and 0.2.0). No fix exists
upstream. This module reimplements the one piece of it actually needed — a
fixed-window counter — directly against `redis.asyncio`, the same INCR+
EXPIRE pattern already used for the per-email login lockout in
`auth_service.py`. See PROGRESS.md for the full story.

Also avoids a real bug in that library's default identifier: it trusts the
client-supplied `X-Forwarded-For` header, which — since this app isn't
behind a proxy that sets/strips it — would let a client bypass the whole
limit just by sending a different value per request (the opposite of
docs/SECURITY.md §69 item 8, "cannot bypass API rate limits"). `RateLimiter`
here only ever uses the actual transport-level `request.client.host`.
"""

from fastapi import Request

from app.core import redis as redis_client
from app.core.config import settings
from app.core.errors import ApiError


class RateLimiter:
    """A fixed-window per-IP limiter: `times` requests per `seconds`,
    grouped under `bucket` — several routes can share one bucket (e.g. face
    registration and face verification both count against
    `face_processing`, since both call the same expensive model).
    """

    def __init__(self, bucket: str, times: int, seconds: int):
        self.bucket = bucket
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        redis = redis_client.get_client()
        if redis is None:
            # Tests override every instance of this dependency to a no-op
            # (see conftest.py) rather than relying on this branch — this is
            # a production safety net for a Redis outage: fail open rather
            # than locking every sensitive endpoint.
            return

        ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{self.bucket}:{ip}"

        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, self.seconds)

        if current > self.times:
            raise ApiError(
                "RATE_LIMITED", "Too many requests. Please try again later.", status_code=429
            )


login_rate_limiter = RateLimiter(
    "login", settings.login_rate_limit_times, settings.login_rate_limit_seconds
)

face_processing_rate_limiter = RateLimiter(
    "face_processing",
    settings.face_processing_rate_limit_times,
    settings.face_processing_rate_limit_seconds,
)

verification_rate_limiter = RateLimiter(
    "verification", settings.verification_rate_limit_times, settings.verification_rate_limit_seconds
)
