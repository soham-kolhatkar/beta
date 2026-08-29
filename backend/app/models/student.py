import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.academic_year import AcademicYear
from app.models.branch import Branch
from app.models.division import Division
from app.models.user import User


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    prn: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    roll_number: Mapped[str] = mapped_column(String, nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("branches.id"), nullable=False, index=True
    )
    division_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("divisions.id"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("academic_years.id"), nullable=False, index=True
    )
    # Set by the Phase 3 face-registration flow; not yet meaningful until then.
    face_registered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(User, foreign_keys=[user_id], lazy="raise")
    branch: Mapped[Branch] = relationship(Branch, foreign_keys=[branch_id], lazy="raise")
    division: Mapped[Division] = relationship(Division, foreign_keys=[division_id], lazy="raise")
    academic_year: Mapped[AcademicYear] = relationship(
        AcademicYear, foreign_keys=[academic_year_id], lazy="raise"
    )
