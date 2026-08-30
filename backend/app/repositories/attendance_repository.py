import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.class_enrollment import ClassEnrollment


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
