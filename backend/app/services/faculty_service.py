from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.class_offering import ClassOffering
from app.models.faculty import Faculty
from app.models.user import User
from app.repositories import (
    class_enrollment_repository,
    class_offering_repository,
    faculty_repository,
)


async def get_my_profile(db: AsyncSession, user: User) -> Faculty:
    faculty = await faculty_repository.get_by_user_id(db, user.id)
    if faculty is None:
        raise ApiError(
            "RESOURCE_NOT_FOUND", "No faculty profile exists for this account.", status_code=404
        )
    return faculty


async def list_my_classes(db: AsyncSession, faculty: Faculty) -> list[tuple[ClassOffering, int]]:
    classes = await class_offering_repository.list_for_faculty(db, faculty.id)
    counts = await class_enrollment_repository.count_by_class_ids(db, [c.id for c in classes])
    return [(c, counts.get(c.id, 0)) for c in classes]
