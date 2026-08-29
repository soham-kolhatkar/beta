from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_faculty, get_current_user
from app.core.database import get_db
from app.models.attendance_session import SessionStatus
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.academic import FacultyClassItem, FacultyClassListResponse, FacultyMeResponse
from app.schemas.attendance import FacultySessionListResponse, SessionDetailResponse
from app.services import attendance_session_service, faculty_service

router = APIRouter(prefix="/faculty", tags=["faculty"])


@router.get("/me", response_model=FacultyMeResponse)
async def get_my_faculty_profile(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Faculty:
    return await faculty_service.get_my_profile(db, current_user)


@router.get("/me/classes", response_model=FacultyClassListResponse)
async def list_my_classes(
    faculty: Faculty = Depends(get_current_faculty), db: AsyncSession = Depends(get_db)
) -> FacultyClassListResponse:
    classes_with_counts = await faculty_service.list_my_classes(db, faculty)
    return FacultyClassListResponse(
        items=[
            FacultyClassItem.from_class_offering(class_offering, count)
            for class_offering, count in classes_with_counts
        ]
    )


@router.get("/me/sessions", response_model=FacultySessionListResponse)
async def list_my_sessions(
    status: SessionStatus | None = None,
    faculty: Faculty = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
) -> FacultySessionListResponse:
    sessions = await attendance_session_service.list_sessions_for_faculty(db, faculty, status)
    return FacultySessionListResponse(
        items=[SessionDetailResponse.from_session(s) for s in sessions]
    )
