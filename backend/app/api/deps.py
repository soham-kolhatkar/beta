from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.models.faculty import Faculty
from app.models.user import User, UserRole
from app.services import auth_service, faculty_service


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    user = await auth_service.get_current_user(db, token) if token else None

    if user is None:
        raise ApiError("AUTH_REQUIRED", "Authentication required.", status_code=401)

    return user


async def get_current_faculty(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Faculty:
    """Reusable faculty-only route guard (docs/SECURITY.md §15). Distinct
    from `faculty_service.get_my_profile`'s own 404 (which fires only for
    the genuinely-anomalous case of a FACULTY-role user with no Faculty
    row): a non-faculty caller hitting a faculty-only endpoint is a role
    mismatch, reported as 403, matching PLAN.md's Phase 4 exit criteria.
    """
    if current_user.role != UserRole.FACULTY:
        raise ApiError("FORBIDDEN", "This action requires a faculty account.", status_code=403)
    return await faculty_service.get_my_profile(db, current_user)
