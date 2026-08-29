import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.attendance_verification import AttendanceVerification


class StartVerificationResponse(BaseModel):
    verification_id: uuid.UUID
    session_id: uuid.UUID
    expires_at: datetime
    steps: list[str] = ["LOCATION", "FACE"]

    @classmethod
    def from_verification(cls, verification: AttendanceVerification) -> "StartVerificationResponse":
        return cls(
            verification_id=verification.id,
            session_id=verification.session_id,
            expires_at=verification.expires_at,
        )


class LocationVerifyRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: float


class LocationVerifyResponse(BaseModel):
    """docs/API.md §28-29. `code`/`message`/`allowed_radius_meters` are only
    populated on failure — the route excludes unset/None fields from the
    JSON so a success response matches §28's example shape exactly, not
    just `verified: true` with a bunch of null keys alongside it.
    """

    verified: bool
    distance_meters: float
    accuracy_meters: float
    next_step: str | None = None
    code: str | None = None
    message: str | None = None
    allowed_radius_meters: float | None = None
