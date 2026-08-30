import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_offering import ClassOffering


async def get_by_id(db: AsyncSession, class_id: uuid.UUID) -> ClassOffering | None:
    result = await db.execute(select(ClassOffering).where(ClassOffering.id == class_id))
    return result.scalar_one_or_none()


async def get_by_id_with_subject(db: AsyncSession, class_id: uuid.UUID) -> ClassOffering | None:
    result = await db.execute(
        select(ClassOffering)
        .where(ClassOffering.id == class_id)
        .options(selectinload(ClassOffering.subject))
    )
    return result.scalar_one_or_none()


async def list_for_faculty(db: AsyncSession, faculty_id: uuid.UUID) -> list[ClassOffering]:
    result = await db.execute(
        select(ClassOffering)
        .where(ClassOffering.faculty_id == faculty_id)
        .options(selectinload(ClassOffering.subject))
        .order_by(ClassOffering.name)
    )
    return list(result.scalars().all())


async def get_by_natural_key(
    db: AsyncSession,
    subject_id: uuid.UUID,
    faculty_id: uuid.UUID,
    division_id: uuid.UUID,
    academic_year_id: uuid.UUID,
) -> ClassOffering | None:
    result = await db.execute(
        select(ClassOffering).where(
            ClassOffering.subject_id == subject_id,
            ClassOffering.faculty_id == faculty_id,
            ClassOffering.division_id == division_id,
            ClassOffering.academic_year_id == academic_year_id,
        )
    )
    return result.scalar_one_or_none()
