import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_year import AcademicYear


async def get_by_institution_and_name(
    db: AsyncSession, institution_id: uuid.UUID, name: str
) -> AcademicYear | None:
    result = await db.execute(
        select(AcademicYear).where(
            AcademicYear.institution_id == institution_id, AcademicYear.name == name
        )
    )
    return result.scalar_one_or_none()
