import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.class_enrollment import ClassEnrollment
from app.models.class_offering import ClassOffering
from app.models.student import Student


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


async def list_students_for_class(db: AsyncSession, class_id: uuid.UUID) -> list[Student]:
    result = await db.execute(
        select(Student)
        .join(ClassEnrollment, ClassEnrollment.student_id == Student.id)
        .where(ClassEnrollment.class_id == class_id)
        .options(selectinload(Student.user))
        .order_by(Student.roll_number)
    )
    return list(result.scalars().all())


async def list_classes_for_student(db: AsyncSession, student_id: uuid.UUID) -> list[ClassOffering]:
    result = await db.execute(
        select(ClassOffering)
        .join(ClassEnrollment, ClassEnrollment.class_id == ClassOffering.id)
        .where(ClassEnrollment.student_id == student_id)
        .options(selectinload(ClassOffering.subject))
        .order_by(ClassOffering.name)
    )
    return list(result.scalars().all())
