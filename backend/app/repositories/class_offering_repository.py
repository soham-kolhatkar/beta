import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_offering import ClassOffering


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
