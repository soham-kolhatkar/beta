import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.attendance import Attendance, AttendanceStatus
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


class FaceVerifyResponse(BaseModel):
    """docs/API.md §30-31. Same shape convention as LocationVerifyResponse:
    a 200 with `verified: false` for a face that was readable but didn't
    match, not the app's `{"error": {...}}` envelope — that's reserved for
    context-level problems (expired, wrong step, etc.), raised as ApiError
    before this schema is even built.
    """

    verified: bool
    next_step: str | None = None
    code: str | None = None
    message: str | None = None
    retryable: bool | None = None


class CompleteAttendanceResponse(BaseModel):
    attendance_id: uuid.UUID
    status: AttendanceStatus
    marked_at: datetime

    @classmethod
    def from_attendance(cls, attendance: Attendance) -> "CompleteAttendanceResponse":
        return cls(
            attendance_id=attendance.id,
            status=attendance.status,
            marked_at=attendance.marked_at,
        )
