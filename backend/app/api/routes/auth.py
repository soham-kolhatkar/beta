from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_KWARGS = {
    "httponly": True,
    "secure": settings.environment == "production",
    "samesite": "lax",
    "path": "/",
}


@router.post("/login", response_model=UserResponse)
async def login(
    payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> User:
    user = await auth_service.authenticate(db, payload.email, payload.password)
    raw_token, expires_at = await auth_service.create_session(db, user)
    await db.commit()

    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_ttl_seconds,
        **_COOKIE_KWARGS,
    )
    return user


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await auth_service.logout(db, token)
        await db.commit()

    response.delete_cookie(key=settings.session_cookie_name, path="/")
