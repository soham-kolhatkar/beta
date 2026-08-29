import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.database import Base


class FaceProfile(Base):
    """A student's face embedding. Kept separate from `students` (rather than
    a column on it) so the model can change later without touching the
    student table — see docs/DATABASE.md §28.
    """

    __tablename__ = "face_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id"), unique=True, nullable=False, index=True
    )
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.face_embedding_dimension), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
