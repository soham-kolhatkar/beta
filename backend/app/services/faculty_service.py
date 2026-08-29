from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.faculty import Faculty
from app.models.user import User
from app.repositories import faculty_repository


async def get_my_profile(db: AsyncSession, user: User) -> Faculty:
    faculty = await faculty_repository.get_by_user_id(db, user.id)
    if faculty is None:
        raise ApiError(
            "RESOURCE_NOT_FOUND", "No faculty profile exists for this account.", status_code=404
        )
    return faculty
