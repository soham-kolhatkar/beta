import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AuditLog(Base):
    """Security-sensitive administrative/security events (docs/DATABASE.md
    §33, resolving the MVP-vs-post-MVP inconsistency between it and
    docs/PRODUCT.md §25 noted in PROGRESS.md — built now, in Phase 7).

    Append-only: nothing in this app updates or deletes a row here.
    `entity_id` has no FK — it points at whichever table `entity_type`
    names, so it can't reference a single column. The Python attribute is
    `details`, not `metadata` — `metadata` is already a reserved attribute
    on every SQLAlchemy declarative model (`Base.metadata`).
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    details: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
