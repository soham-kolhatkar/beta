import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.class_offering import ClassOffering
from app.models.faculty import Faculty


class SessionStatus(str, enum.Enum):
    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"


class AttendanceSession(Base):
    """A specific attendance opportunity for a class (docs/DATABASE.md §20).

    `ended_at` is not in the docs schema but is required by the `/end`
    response shape (docs/API.md §22); added here as a small, deliberate
    schema addition (see PROGRESS.md).

    There is no background job transitioning an expired-but-not-explicitly-
    ended ACTIVE session to ENDED (docs/DATABASE.md §21 says expired sessions
    "should transition logically" to inactive, but specifies no mechanism).
    Code that needs to know whether a session can currently accept
    attendance checks `status == ACTIVE` *and* `now` is within
    [starts_at, ends_at] rather than relying on `status` alone.
    """

    __tablename__ = "attendance_sessions"
    __table_args__ = (
        # docs/DATABASE.md §38 indexing recommendations.
        Index("ix_attendance_sessions_class_id_status", "class_id", "status"),
        Index("ix_attendance_sessions_starts_at_ends_at_status", "starts_at", "ends_at", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id"), nullable=False, index=True
    )
    faculty_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("faculty.id"), nullable=False, index=True
    )

    latitude: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6, asdecimal=False), nullable=False)
    radius_meters: Mapped[float] = mapped_column(Numeric(6, 2, asdecimal=False), nullable=False)

    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"), nullable=False, default=SessionStatus.ACTIVE
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    class_offering: Mapped[ClassOffering] = relationship(
        ClassOffering, foreign_keys=[class_id], lazy="raise"
    )
    faculty: Mapped[Faculty] = relationship(Faculty, foreign_keys=[faculty_id], lazy="raise")
