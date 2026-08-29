import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.faculty import Faculty


async def get_by_employee_id(db: AsyncSession, employee_id: str) -> Faculty | None:
    result = await db.execute(select(Faculty).where(Faculty.employee_id == employee_id))
    return result.scalar_one_or_none()


async def get_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Faculty | None:
    result = await db.execute(
        select(Faculty).where(Faculty.user_id == user_id).options(selectinload(Faculty.user))
    )
    return result.scalar_one_or_none()
