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
    attendance_repository,
    attendance_session_repository,
    attendance_verification_repository,
    class_enrollment_repository,
    class_offering_repository,
    faculty_repository,
    student_repository,
)
from app.schemas.attendance import (
    RosterSessionBrief,
    RosterStatus,
    RosterStudentItem,
    RosterSummary,
    SessionCreateRequest,
    SessionRosterResponse,
)


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


async def get_session_roster(
    db: AsyncSession, faculty: Faculty, session_id: uuid.UUID
) -> SessionRosterResponse:
    """docs/API.md §24. `students`/`attendance`/`verification-attempt` are
    fetched as three separate queries and combined in Python rather than
    one big join — the roster size is small (one division's worth of
    students), so this keeps each query simple over saving a round trip.
    """
    session = await attendance_session_repository.get_by_id(db, session_id)
    if session is None:
        raise ApiError("SESSION_NOT_FOUND", "Session not found.", status_code=404)
    if session.faculty_id != faculty.id:
        raise ApiError("FORBIDDEN", "You are not authorized to view this session.", status_code=403)

    students = await class_enrollment_repository.list_students_for_class(db, session.class_id)
    attendance_by_student = {
        row.student_id: row for row in await attendance_repository.list_by_session(db, session.id)
    }
    attempted_student_ids = await attendance_verification_repository.list_student_ids_with_attempts(
        db, session.id
    )

    items: list[RosterStudentItem] = []
    present = not_marked = verification_issues = 0

    for student in students:
        attendance = attendance_by_student.get(student.id)
        status: RosterStatus
        if attendance is not None:
            status, marked_at = "PRESENT", attendance.marked_at
            present += 1
        elif student.id in attempted_student_ids:
            status, marked_at = "VERIFICATION_ISSUE", None
            verification_issues += 1
        else:
            status, marked_at = "NOT_MARKED", None
            not_marked += 1

        items.append(
            RosterStudentItem(
                student_id=student.id,
                name=student.user.name,
                prn=student.prn,
                status=status,
                marked_at=marked_at,
            )
        )

    return SessionRosterResponse(
        session=RosterSessionBrief(
            id=session.id,
            class_name=session.class_offering.name,
            subject=session.class_offering.subject.name,
        ),
        summary=RosterSummary(
            total_students=len(students),
            present=present,
            not_marked=not_marked,
            verification_issues=verification_issues,
        ),
        students=items,
    )
