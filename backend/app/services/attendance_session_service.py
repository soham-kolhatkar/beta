import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ApiError
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.faculty import Faculty
from app.models.student import Student
from app.models.user import User, UserRole
from app.repositories import (
    attendance_session_repository,
    class_enrollment_repository,
    class_offering_repository,
    faculty_repository,
    student_repository,
)
from app.schemas.attendance import SessionCreateRequest


async def create_session(
    db: AsyncSession, faculty: Faculty, payload: SessionCreateRequest
) -> AttendanceSession:
    class_offering = await class_offering_repository.get_by_id(db, payload.class_id)
    if class_offering is None:
        raise ApiError("RESOURCE_NOT_FOUND", "Class not found.", status_code=404)
    if class_offering.faculty_id != faculty.id:
        raise ApiError(
            "FORBIDDEN",
            "You are not authorized to create sessions for this class.",
            status_code=403,
        )

    now = datetime.now(timezone.utc)

    if payload.starts_at >= payload.ends_at:
        raise ApiError(
            "INVALID_REQUEST", "Session start time must be before its end time.", status_code=422
        )
    if payload.ends_at <= now:
        raise ApiError(
            "INVALID_REQUEST", "Session end time must be in the future.", status_code=422
        )
    if not (-90 <= payload.latitude <= 90) or not (-180 <= payload.longitude <= 180):
        raise ApiError("INVALID_REQUEST", "Invalid coordinates.", status_code=422)
    if not (
        settings.session_min_radius_meters
        <= payload.radius_meters
        <= settings.session_max_radius_meters
    ):
        raise ApiError(
            "INVALID_REQUEST",
            f"Radius must be between {settings.session_min_radius_meters:.0f} and "
            f"{settings.session_max_radius_meters:.0f} meters.",
            status_code=422,
        )

    conflict = await attendance_session_repository.get_active_conflict(
        db, class_offering.id, payload.starts_at, payload.ends_at, now
    )
    if conflict is not None:
        raise ApiError(
            "SESSION_CONFLICT", "An active session already exists for this class.", status_code=409
        )

    session = await attendance_session_repository.create(
        db,
        class_id=class_offering.id,
        faculty_id=faculty.id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_meters=payload.radius_meters,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
    )
    await db.commit()
    return session


async def end_session(
    db: AsyncSession, faculty: Faculty, session_id: uuid.UUID
) -> AttendanceSession:
    session = await attendance_session_repository.get_by_id(db, session_id)
    if session is None:
        raise ApiError("SESSION_NOT_FOUND", "Session not found.", status_code=404)
    if session.faculty_id != faculty.id:
        raise ApiError(
            "FORBIDDEN", "You are not authorized to manage this session.", status_code=403
        )

    # Idempotent: ending an already-ended session just returns its current
    # state rather than erroring (e.g. a double-click under a slow network).
    if session.status != SessionStatus.ENDED:
        session.status = SessionStatus.ENDED
        session.ended_at = datetime.now(timezone.utc)
        await db.commit()

    return session


async def get_session_for_user(
    db: AsyncSession, user: User, session_id: uuid.UUID
) -> AttendanceSession:
    session = await attendance_session_repository.get_by_id(db, session_id)
    if session is None:
        raise ApiError("SESSION_NOT_FOUND", "Session not found.", status_code=404)

    not_authorized = ApiError(
        "FORBIDDEN", "You are not authorized to view this session.", status_code=403
    )

    if user.role == UserRole.FACULTY:
        faculty = await faculty_repository.get_by_user_id(db, user.id)
        if faculty is None or session.faculty_id != faculty.id:
            raise not_authorized
    elif user.role == UserRole.STUDENT:
        student = await student_repository.get_by_user_id(db, user.id)
        enrollment = (
            await class_enrollment_repository.get_by_class_and_student(
                db, session.class_id, student.id
            )
            if student is not None
            else None
        )
        if enrollment is None:
            raise not_authorized
    else:
        raise not_authorized

    return session


async def list_active_sessions_for_student(
    db: AsyncSession, student: Student
) -> list[AttendanceSession]:
    now = datetime.now(timezone.utc)
    return await attendance_session_repository.list_active_for_student(db, student.id, now)


async def list_sessions_for_faculty(
    db: AsyncSession, faculty: Faculty, status: SessionStatus | None
) -> list[AttendanceSession]:
    return await attendance_session_repository.list_for_faculty(db, faculty.id, status)
