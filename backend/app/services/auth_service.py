from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

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


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await user_repository.get_by_email(db, email)

    if user is None:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        raise ApiError("INVALID_CREDENTIALS", "Incorrect email or password.", status_code=401)

    if not verify_password(password, user.password_hash) or not user.is_active:
        raise ApiError("INVALID_CREDENTIALS", "Incorrect email or password.", status_code=401)

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
