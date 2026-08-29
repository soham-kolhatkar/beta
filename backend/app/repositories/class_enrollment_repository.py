import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.class_enrollment import ClassEnrollment


async def get_by_class_and_student(
    db: AsyncSession, class_id: uuid.UUID, student_id: uuid.UUID
) -> ClassEnrollment | None:
    result = await db.execute(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == class_id, ClassEnrollment.student_id == student_id
        )
    )
    return result.scalar_one_or_none()


async def count_by_class_ids(db: AsyncSession, class_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not class_ids:
        return {}

    result = await db.execute(
        select(ClassEnrollment.class_id, func.count())
        .where(ClassEnrollment.class_id.in_(class_ids))
        .group_by(ClassEnrollment.class_id)
    )
    return dict(result.all())
