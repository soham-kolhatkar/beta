from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.student import Student
from app.models.user import User
from app.repositories import student_repository


async def get_my_profile(db: AsyncSession, user: User) -> Student:
    student = await student_repository.get_by_user_id(db, user.id)
    if student is None:
        raise ApiError(
            "RESOURCE_NOT_FOUND", "No student profile exists for this account.", status_code=404
        )
    return student
