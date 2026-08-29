import uuid

from sqlalchemy import select
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
