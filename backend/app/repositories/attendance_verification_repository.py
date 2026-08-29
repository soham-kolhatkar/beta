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
