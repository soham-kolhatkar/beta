import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_verification import AttendanceVerification, VerificationStatus


async def create(
    db: AsyncSession, session_id: uuid.UUID, student_id: uuid.UUID, expires_at: datetime
) -> AttendanceVerification:
    verification = AttendanceVerification(
        session_id=session_id,
        student_id=student_id,
        status=VerificationStatus.CREATED,
        expires_at=expires_at,
    )
    db.add(verification)
    await db.flush()
    return verification


async def get_by_id(db: AsyncSession, verification_id: uuid.UUID) -> AttendanceVerification | None:
    result = await db.execute(
        select(AttendanceVerification).where(AttendanceVerification.id == verification_id)
    )
    return result.scalar_one_or_none()


async def list_student_ids_with_attempts(db: AsyncSession, session_id: uuid.UUID) -> set[uuid.UUID]:
    """Students who started at least one verification attempt for this
    session, whether or not it ever succeeded — used to distinguish "tried
    and failed" from "never even attempted" on the faculty roster.
    """
    result = await db.execute(
        select(AttendanceVerification.student_id)
        .where(AttendanceVerification.session_id == session_id)
        .distinct()
    )
    return set(result.scalars().all())
