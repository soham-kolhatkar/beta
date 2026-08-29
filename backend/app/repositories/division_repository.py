import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.division import Division


async def get_by_branch_year_name(
    db: AsyncSession, branch_id: uuid.UUID, academic_year_id: uuid.UUID, name: str
) -> Division | None:
    result = await db.execute(
        select(Division).where(
            Division.branch_id == branch_id,
            Division.academic_year_id == academic_year_id,
            Division.name == name,
        )
    )
    return result.scalar_one_or_none()
