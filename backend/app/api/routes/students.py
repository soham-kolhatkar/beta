from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.student import Student
from app.models.user import User
from app.schemas.academic import StudentMeResponse
from app.services import student_service

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me", response_model=StudentMeResponse)
async def get_my_student_profile(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Student:
    return await student_service.get_my_profile(db, current_user)
