import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.attendance import AttendanceStatus
from app.models.student import Student
from app.models.user import User
from app.schemas.academic import StudentMeResponse
from app.schemas.dashboard import StudentDashboardResponse
from app.schemas.face import FaceModelInfo, FaceRegisterResponse, FaceStatusResponse
from app.schemas.history import (
    AttendanceHistoryResponse,
    AttendanceSummaryResponse,
    ClassAttendanceResponse,
)
from app.services import face_service, student_service

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me", response_model=StudentMeResponse)
async def get_my_student_profile(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Student:
    return await student_service.get_my_profile(db, current_user)


@router.get("/me/dashboard", response_model=StudentDashboardResponse)
async def get_my_dashboard(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> StudentDashboardResponse:
    student = await student_service.get_my_profile(db, current_user)
    return await student_service.get_dashboard(db, student)


@router.get("/me/attendance", response_model=AttendanceHistoryResponse)
async def get_my_attendance_history(
    subject_id: uuid.UUID | None = None,
    status: AttendanceStatus | None = None,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttendanceHistoryResponse:
    student = await student_service.get_my_profile(db, current_user)
    return await student_service.get_attendance_history(
        db,
        student,
        subject_id=subject_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get("/me/attendance/summary", response_model=AttendanceSummaryResponse)
async def get_my_attendance_summary(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AttendanceSummaryResponse:
    student = await student_service.get_my_profile(db, current_user)
    return await student_service.get_attendance_summary(db, student)


@router.get("/me/classes/{class_id}/attendance", response_model=ClassAttendanceResponse)
async def get_my_class_attendance(
    class_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClassAttendanceResponse:
    student = await student_service.get_my_profile(db, current_user)
    return await student_service.get_class_attendance(db, student, class_id)


@router.post("/me/face", response_model=FaceRegisterResponse)
async def register_my_face(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FaceRegisterResponse:
    student = await student_service.get_my_profile(db, current_user)
    raw = await image.read()
    profile = await face_service.register_face(db, student, image.content_type, raw)
    return FaceRegisterResponse(
        face_registered=True,
        model=FaceModelInfo(name=profile.model_name, version=profile.model_version),
    )


@router.get("/me/face", response_model=FaceStatusResponse)
async def get_my_face_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> FaceStatusResponse:
    student = await student_service.get_my_profile(db, current_user)
    profile = await face_service.get_face_status(db, student)

    if profile is None:
        return FaceStatusResponse(registered=False)

    return FaceStatusResponse(
        registered=True,
        model=FaceModelInfo(name=profile.model_name, version=profile.model_version),
        updated_at=profile.updated_at,
    )
