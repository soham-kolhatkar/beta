import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_faculty, get_current_user
from app.core.database import get_db
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
)
from app.services import attendance_session_service, student_service

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


@router.post("/sessions/{session_id}/end", response_model=SessionEndResponse)
async def end_session(
    session_id: uuid.UUID,
    faculty: Faculty = Depends(get_current_faculty),
    db: AsyncSession = Depends(get_db),
) -> AttendanceSession:
    return await attendance_session_service.end_session(db, faculty, session_id)
