from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.models.user import User
from app.services import auth_service


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    user = await auth_service.get_current_user(db, token) if token else None

    if user is None:
        raise ApiError("AUTH_REQUIRED", "Authentication required.", status_code=401)

    return user
