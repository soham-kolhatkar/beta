import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.class_enrollment import ClassEnrollment
from app.models.class_offering import ClassOffering
from app.models.faculty import Faculty

_EAGER_LOAD_OPTIONS = (
    selectinload(AttendanceSession.class_offering).selectinload(ClassOffering.subject),
    selectinload(AttendanceSession.faculty).selectinload(Faculty.user),
)


async def create(
    db: AsyncSession,
    class_id: uuid.UUID,
    faculty_id: uuid.UUID,
    latitude: float,
    longitude: float,
    radius_meters: float,
    starts_at: datetime,
    ends_at: datetime,
) -> AttendanceSession:
    session = AttendanceSession(
        class_id=class_id,
        faculty_id=faculty_id,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        starts_at=starts_at,
        ends_at=ends_at,
        status=SessionStatus.ACTIVE,
    )
    db.add(session)
    await db.flush()
    return session


async def get_by_id(db: AsyncSession, session_id: uuid.UUID) -> AttendanceSession | None:
    result = await db.execute(
        select(AttendanceSession)
        .where(AttendanceSession.id == session_id)
        .options(*_EAGER_LOAD_OPTIONS)
    )
    return result.scalar_one_or_none()


async def get_active_conflict(
    db: AsyncSession, class_id: uuid.UUID, starts_at: datetime, ends_at: datetime, now: datetime
) -> AttendanceSession | None:
    """Any ACTIVE, not-yet-expired session for this class whose window
    overlaps [starts_at, ends_at) (docs/API.md §42: no overlapping active
    sessions per class). An ACTIVE row past its own `ends_at` is treated as
    expired, not a live conflict — see AttendanceSession's docstring.
    """
    result = await db.execute(
        select(AttendanceSession).where(
            AttendanceSession.class_id == class_id,
            AttendanceSession.status == SessionStatus.ACTIVE,
            AttendanceSession.ends_at > now,
            AttendanceSession.starts_at < ends_at,
            AttendanceSession.ends_at > starts_at,
        )
    )
    return result.scalars().first()


async def list_active_for_student(
    db: AsyncSession, student_id: uuid.UUID, now: datetime
) -> list[AttendanceSession]:
    result = await db.execute(
        select(AttendanceSession)
        .join(ClassEnrollment, ClassEnrollment.class_id == AttendanceSession.class_id)
        .where(
            ClassEnrollment.student_id == student_id,
            AttendanceSession.status == SessionStatus.ACTIVE,
            AttendanceSession.starts_at <= now,
            AttendanceSession.ends_at > now,
        )
        .options(*_EAGER_LOAD_OPTIONS)
        .order_by(AttendanceSession.starts_at)
    )
    return list(result.scalars().all())


async def list_for_faculty(
    db: AsyncSession, faculty_id: uuid.UUID, status: SessionStatus | None = None
) -> list[AttendanceSession]:
    query = select(AttendanceSession).where(AttendanceSession.faculty_id == faculty_id)
    if status is not None:
        query = query.where(AttendanceSession.status == status)
    query = query.options(*_EAGER_LOAD_OPTIONS).order_by(AttendanceSession.starts_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())
