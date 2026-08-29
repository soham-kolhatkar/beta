from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.academic import FacultyMeResponse
from app.services import faculty_service

router = APIRouter(prefix="/faculty", tags=["faculty"])


@router.get("/me", response_model=FacultyMeResponse)
async def get_my_faculty_profile(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Faculty:
    return await faculty_service.get_my_profile(db, current_user)
