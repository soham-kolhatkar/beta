import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attendance import Attendance, AttendanceStatus
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.class_enrollment import ClassEnrollment
from app.models.class_offering import ClassOffering

_HISTORY_EAGER_LOAD = (
    selectinload(Attendance.session)
    .selectinload(AttendanceSession.class_offering)
    .selectinload(ClassOffering.subject)
)


async def create(
    db: AsyncSession,
    session_id: uuid.UUID,
    student_id: uuid.UUID,
    marked_at: datetime,
    latitude: float,
    longitude: float,
    location_accuracy: float,
    distance_meters: float,
    face_verified: bool,
    face_score: float | None,
) -> Attendance:
    attendance = Attendance(
        session_id=session_id,
        student_id=student_id,
        marked_at=marked_at,
        latitude=latitude,
        longitude=longitude,
        location_accuracy=location_accuracy,
        distance_meters=distance_meters,
        face_verified=face_verified,
        face_score=face_score,
    )
    db.add(attendance)
    await db.flush()
    return attendance


async def get_by_session_and_student(
    db: AsyncSession, session_id: uuid.UUID, student_id: uuid.UUID
) -> Attendance | None:
    result = await db.execute(
        select(Attendance).where(
            Attendance.session_id == session_id, Attendance.student_id == student_id
        )
    )
    return result.scalar_one_or_none()


async def list_by_session(db: AsyncSession, session_id: uuid.UUID) -> list[Attendance]:
    result = await db.execute(select(Attendance).where(Attendance.session_id == session_id))
    return list(result.scalars().all())


async def count_by_student(db: AsyncSession, student_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Attendance).where(Attendance.student_id == student_id)
    )
    return result.scalar_one()


async def count_ended_sessions_for_student(
    db: AsyncSession, student_id: uuid.UUID, now: datetime
) -> int:
    """The denominator for a student's attendance percentage: sessions for
    classes they're enrolled in that have actually happened (ended
    explicitly, or simply past their own `ends_at` — same "don't trust
    status alone" reasoning as `AttendanceSession`'s own docstring), not
    sessions still upcoming or in progress.
    """
    result = await db.execute(
        select(func.count())
        .select_from(AttendanceSession)
        .join(ClassEnrollment, ClassEnrollment.class_id == AttendanceSession.class_id)
        .where(
            ClassEnrollment.student_id == student_id,
            (AttendanceSession.status == SessionStatus.ENDED) | (AttendanceSession.ends_at <= now),
        )
    )
    return result.scalar_one()


async def list_for_student(
    db: AsyncSession,
    student_id: uuid.UUID,
    *,
    subject_id: uuid.UUID | None = None,
    status: AttendanceStatus | None = None,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Attendance], int]:
    """Paginated, filterable history for GET /students/me/attendance
    (docs/API.md §14). `subject_id` filters by the Subject, not the
    ClassOffering (docs/API.md consistently distinguishes the two) — joins
    through the session's class to reach it.
    """
    conditions = [Attendance.student_id == student_id]
    if subject_id is not None:
        conditions.append(ClassOffering.subject_id == subject_id)
    if status is not None:
        conditions.append(Attendance.status == status)
    if from_dt is not None:
        conditions.append(Attendance.marked_at >= from_dt)
    if to_dt is not None:
        conditions.append(Attendance.marked_at < to_dt)

    joined = (
        select(Attendance.id)
        .join(AttendanceSession, AttendanceSession.id == Attendance.session_id)
        .join(ClassOffering, ClassOffering.id == AttendanceSession.class_id)
        .where(*conditions)
    )
    total = (await db.execute(select(func.count()).select_from(joined.subquery()))).scalar_one()

    items_query = (
        select(Attendance)
        .join(AttendanceSession, AttendanceSession.id == Attendance.session_id)
        .join(ClassOffering, ClassOffering.id == AttendanceSession.class_id)
        .where(*conditions)
        .options(_HISTORY_EAGER_LOAD)
        .order_by(Attendance.marked_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(items_query)).scalars().all()
    return list(items), total


async def list_for_student_and_class(
    db: AsyncSession, student_id: uuid.UUID, class_id: uuid.UUID
) -> list[Attendance]:
    """All of a student's attendance records for one class (docs/API.md
    §15's `records` list) — unpaginated, since a single class's session
    count is small enough not to need it.
    """
    result = await db.execute(
        select(Attendance)
        .join(AttendanceSession, AttendanceSession.id == Attendance.session_id)
        .where(Attendance.student_id == student_id, AttendanceSession.class_id == class_id)
        .options(_HISTORY_EAGER_LOAD)
        .order_by(Attendance.marked_at.desc())
    )
    return list(result.scalars().all())


async def count_present_by_class_for_student(
    db: AsyncSession, student_id: uuid.UUID, class_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not class_ids:
        return {}

    result = await db.execute(
        select(AttendanceSession.class_id, func.count())
        .select_from(Attendance)
        .join(AttendanceSession, AttendanceSession.id == Attendance.session_id)
        .where(Attendance.student_id == student_id, AttendanceSession.class_id.in_(class_ids))
        .group_by(AttendanceSession.class_id)
    )
    return dict(result.all())
