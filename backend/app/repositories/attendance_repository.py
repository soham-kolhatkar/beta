import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance


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
