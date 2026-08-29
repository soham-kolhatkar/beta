import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.student import Student


async def get_by_prn(db: AsyncSession, prn: str) -> Student | None:
    result = await db.execute(select(Student).where(Student.prn == prn))
    return result.scalar_one_or_none()


async def get_by_user_id(db: AsyncSession, user_id: uuid.UUID) -> Student | None:
    result = await db.execute(
        select(Student)
        .where(Student.user_id == user_id)
        .options(
            selectinload(Student.user),
            selectinload(Student.branch),
            selectinload(Student.division),
            selectinload(Student.academic_year),
        )
    )
    return result.scalar_one_or_none()
