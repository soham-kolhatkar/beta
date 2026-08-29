import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subject import Subject


async def get_by_institution_and_code(
    db: AsyncSession, institution_id: uuid.UUID, code: str
) -> Subject | None:
    result = await db.execute(
        select(Subject).where(Subject.institution_id == institution_id, Subject.code == code)
    )
    return result.scalar_one_or_none()
