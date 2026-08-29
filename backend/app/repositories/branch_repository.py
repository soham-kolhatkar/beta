import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch


async def get_by_institution_and_code(
    db: AsyncSession, institution_id: uuid.UUID, code: str
) -> Branch | None:
    result = await db.execute(
        select(Branch).where(Branch.institution_id == institution_id, Branch.code == code)
    )
    return result.scalar_one_or_none()
