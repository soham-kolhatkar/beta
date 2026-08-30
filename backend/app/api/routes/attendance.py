import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_faculty, get_current_user
from app.core.database import get_db
from app.core.rate_limit import face_processing_rate_limiter, verification_rate_limiter
from app.models.attendance_session import AttendanceSession
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.attendance import (
    ActiveSessionItem,
    ActiveSessionListResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionDetailResponse,
    SessionEndResponse,
    SessionRosterResponse,
)
from app.schemas.verification import (
    CompleteAttendanceResponse,
    FaceVerifyResponse,
    LocationVerifyRequest,
    LocationVerifyResponse,
    StartVerificationResponse,
)
from app.services import attendance_session_service, student_service, verification_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session(
    payload: SessionCreateRequest,
    faculty: Faculty = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
) -> AttendanceSession:
    return await attendance_session_service.create_session(db, faculty, payload)


# Registered before /sessions/{session_id}: Starlette matches routes in
# registration order, and "active" would otherwise be captured by the
# dynamic segment and fail UUID parsing.
@router.get("/sessions/active", response_model=ActiveSessionListResponse)
async def list_active_sessions(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ActiveSessionListResponse:
    student = await student_service.get_my_profile(db, current_user)
    sessions = await attendance_session_service.list_active_sessions_for_student(db, student)
    return ActiveSessionListResponse(items=[ActiveSessionItem.from_session(s) for s in sessions])


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionDetailResponse:
    session = await attendance_session_service.get_session_for_user(db, current_user, session_id)
    return SessionDetailResponse.from_session(session)


@router.get("/sessions/{session_id}/attendance", response_model=SessionRosterResponse)
async def get_session_roster(
    session_id: uuid.UUID,
    faculty: Faculty = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
) -> SessionRosterResponse:
    return await attendance_session_service.get_session_roster(db, faculty, session_id)


@router.post("/sessions/{session_id}/end", response_model=SessionEndResponse)
async def end_session(
    session_id: uuid.UUID,
    faculty: Faculty = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
) -> AttendanceSession:
    return await attendance_session_service.end_session(db, faculty, session_id)


@router.post(
    "/sessions/{session_id}/verification",
    response_model=StartVerificationResponse,
    dependencies=[Depends(verification_rate_limiter)],
)
async def start_verification(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StartVerificationResponse:
    student = await student_service.get_my_profile(db, current_user)
    verification = await verification_service.start_verification(db, student, session_id)
    return StartVerificationResponse.from_verification(verification)


@router.post(
    "/verifications/{verification_id}/location",
    response_model=LocationVerifyResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(verification_rate_limiter)],
)
async def submit_location_verification(
    verification_id: uuid.UUID,
    payload: LocationVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocationVerifyResponse:
    student = await student_service.get_my_profile(db, current_user)
    return await verification_service.submit_location(db, student, verification_id, payload)


@router.post(
    "/verifications/{verification_id}/face",
    response_model=FaceVerifyResponse,
    response_model_exclude_none=True,
    dependencies=[Depends(face_processing_rate_limiter)],
)
async def submit_face_verification(
    verification_id: uuid.UUID,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FaceVerifyResponse:
    student = await student_service.get_my_profile(db, current_user)
    raw = await image.read()
    return await verification_service.submit_face(
        db, student, verification_id, image.content_type, raw
    )


@router.post(
    "/verifications/{verification_id}/complete",
    response_model=CompleteAttendanceResponse,
    dependencies=[Depends(verification_rate_limiter)],
)
async def complete_verification(
    verification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompleteAttendanceResponse:
    student = await student_service.get_my_profile(db, current_user)
    return await verification_service.complete_verification(db, student, verification_id)
