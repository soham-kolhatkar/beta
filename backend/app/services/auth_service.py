from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import redis as redis_client
from app.core.config import settings
from app.core.errors import ApiError
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    verify_password,
)
from app.models.user import User
from app.repositories import session_repository, user_repository

# Hashed once at import time so the "email not found" path still pays the
# Argon2 verification cost, keeping login response time similar regardless of
# whether the email is registered (docs/SECURITY.md §6 account-enumeration
# resistance).
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-password")


def _lockout_key(email: str) -> str:
    return f"login_lockout:{email}"


async def _check_email_lockout(email: str) -> None:
    """docs/SECURITY.md §65: rate limit by both IP (the route-level
    fastapi-limiter dependency) and target email — a distributed attacker
    rotating IPs can still only exhaust this one account's own counter.
    Deliberately failure-only (see `authenticate` below) and separate from
    the IP limiter's per-request model, so it's tracked directly against
    Redis rather than through fastapi-limiter. No-ops if Redis isn't
    available (tests; or a down Redis in production — fails open rather
    than locking out every login, since the IP-based limiter is still an
    active layer either way).
    """
    redis = redis_client.get_client()
    if redis is None:
        return

    attempts = await redis.get(_lockout_key(email))
    if attempts is not None and int(attempts) >= settings.auth_email_lockout_max_attempts:
        raise ApiError(
            "RATE_LIMITED",
            "Too many login attempts for this account. Try again later.",
            status_code=429,
        )


async def _record_login_failure(email: str) -> None:
    redis = redis_client.get_client()
    if redis is None:
        return

    key = _lockout_key(email)
    attempts = await redis.incr(key)
    if attempts == 1:
        await redis.expire(key, settings.auth_email_lockout_window_seconds)


async def _clear_login_failures(email: str) -> None:
    redis = redis_client.get_client()
    if redis is not None:
        await redis.delete(_lockout_key(email))


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    await _check_email_lockout(normalized_email)

    user = await user_repository.get_by_email(db, normalized_email)

    if user is None:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        await _record_login_failure(normalized_email)
        raise ApiError("INVALID_CREDENTIALS", "Incorrect email or password.", status_code=401)

    if not verify_password(password, user.password_hash) or not user.is_active:
        await _record_login_failure(normalized_email)
        raise ApiError("INVALID_CREDENTIALS", "Incorrect email or password.", status_code=401)

    await _clear_login_failures(normalized_email)
    return user


async def create_session(db: AsyncSession, user: User) -> tuple[str, datetime]:
    raw_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.session_ttl_seconds)
    await session_repository.create(db, user.id, hash_session_token(raw_token), expires_at)
    return raw_token, expires_at


async def get_current_user(db: AsyncSession, raw_token: str) -> User | None:
    token_hash = hash_session_token(raw_token)
    session = await session_repository.get_by_token_hash(db, token_hash)
    if session is None:
        return None

    if session.expires_at < datetime.now(timezone.utc):
        await session_repository.delete_by_token_hash(db, token_hash)
        return None

    user = await user_repository.get_by_id(db, session.user_id)
    if user is None or not user.is_active:
        return None

    return user


async def logout(db: AsyncSession, raw_token: str) -> None:
    await session_repository.delete_by_token_hash(db, hash_session_token(raw_token))
