import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.attendance_session import AttendanceSession
from app.models.student import Student


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"


class Attendance(Base):
    """A marked attendance record (docs/DATABASE.md §24). Snapshots the
    location/face results at the moment of completion rather than joining
    back to `attendance_verifications` for them — that context is
    short-lived (docs/API.md §35) and not meant to be the durable record of
    why attendance was granted.

    `UNIQUE(session_id, student_id)` is the single most important
    constraint in the system (docs/DATABASE.md §25, docs/ARCHITECTURE.md
    §25): the database is the final defense against duplicate attendance
    under concurrent requests, not just the service-level pre-check.
    """

    __tablename__ = "attendance"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_attendance_session_student"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_sessions.id"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id"), nullable=False, index=True
    )

    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    latitude: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False)
    location_accuracy: Mapped[float] = mapped_column(Numeric(7, 2, asdecimal=False), nullable=False)
    distance_meters: Mapped[float] = mapped_column(Numeric(8, 2, asdecimal=False), nullable=False)

    face_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    face_score: Mapped[float | None] = mapped_column(Numeric(6, 4, asdecimal=False), nullable=True)

    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status"),
        nullable=False,
        default=AttendanceStatus.PRESENT,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[AttendanceSession] = relationship(
        AttendanceSession, foreign_keys=[session_id], lazy="raise"
    )
    student: Mapped[Student] = relationship(Student, foreign_keys=[student_id], lazy="raise")
