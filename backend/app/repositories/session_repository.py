import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import UserSession


async def create(
    db: AsyncSession, user_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> UserSession:
    session = UserSession(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    db.add(session)
    await db.flush()
    return session


async def get_by_token_hash(db: AsyncSession, token_hash: str) -> UserSession | None:
    result = await db.execute(select(UserSession).where(UserSession.token_hash == token_hash))
    return result.scalar_one_or_none()


async def delete_by_token_hash(db: AsyncSession, token_hash: str) -> None:
    await db.execute(delete(UserSession).where(UserSession.token_hash == token_hash))
