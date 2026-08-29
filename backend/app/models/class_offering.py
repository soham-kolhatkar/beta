import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.division import Division
from app.models.faculty import Faculty
from app.models.subject import Subject


class ClassOffering(Base):
    """A specific teaching offering (subject + faculty + division + year).

    Named `ClassOffering` in Python (not `Class`, to avoid reading oddly next
    to the `class` keyword everywhere in this codebase) but kept as the
    `classes` table to match every other doc/endpoint reference
    (docs/DATABASE.md §16 flags `course_offering`/`class_offering` as a
    possible future rename of the *table*, not adopted here to avoid
    diverging from the rest of the spec).
    """

    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institutions.id"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id"), nullable=False, index=True
    )
    faculty_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("faculty.id"), nullable=False, index=True
    )
    division_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("divisions.id"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("academic_years.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    subject: Mapped[Subject] = relationship(Subject, foreign_keys=[subject_id], lazy="raise")
    faculty: Mapped[Faculty] = relationship(Faculty, foreign_keys=[faculty_id], lazy="raise")
    division: Mapped[Division] = relationship(Division, foreign_keys=[division_id], lazy="raise")
