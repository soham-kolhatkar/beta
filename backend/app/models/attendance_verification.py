import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.attendance_session import AttendanceSession
from app.models.student import Student


class VerificationStatus(str, enum.Enum):
    CREATED = "CREATED"
    LOCATION_VERIFIED = "LOCATION_VERIFIED"
    FACE_VERIFIED = "FACE_VERIFIED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class AttendanceVerification(Base):
    """The short-lived verification-context state machine from
    docs/API.md §26-35. Not in docs/DATABASE.md's original entity list —
    that doc's `attendance_verification_attempts` (§27) is a one-row-per-
    completed-attempt audit log, not a mutable in-flight context with a
    `status`/`expires_at`. This table fills that gap; see docs/DATABASE.md
    §27a. The audit-log table itself remains an optional, separate,
    not-yet-built concern (still "optional for MVP" per that section).

    Face-step columns (`face_result`, `face_score`, ...) are deliberately
    not added yet — Phase 5b adds those when it builds the face step,
    rather than adding unused columns now.
    """

    __tablename__ = "attendance_verifications"
    __table_args__ = (
        Index("ix_attendance_verifications_session_id_student_id", "session_id", "student_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_sessions.id"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id"), nullable=False, index=True
    )

    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status"),
        nullable=False,
        default=VerificationStatus.CREATED,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    location_latitude: Mapped[float | None] = mapped_column(
        Numeric(9, 6, asdecimal=False), nullable=True
    )
    location_longitude: Mapped[float | None] = mapped_column(
        Numeric(9, 6, asdecimal=False), nullable=True
    )
    location_accuracy_meters: Mapped[float | None] = mapped_column(
        Numeric(7, 2, asdecimal=False), nullable=True
    )
    location_distance_meters: Mapped[float | None] = mapped_column(
        Numeric(8, 2, asdecimal=False), nullable=True
    )

    failure_reason: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped[AttendanceSession] = relationship(
        AttendanceSession, foreign_keys=[session_id], lazy="raise"
    )
    student: Mapped[Student] = relationship(Student, foreign_keys=[student_id], lazy="raise")
