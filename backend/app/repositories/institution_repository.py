from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Institution


async def get_by_code(db: AsyncSession, code: str) -> Institution | None:
    result = await db.execute(select(Institution).where(Institution.code == code))
    return result.scalar_one_or_none()
