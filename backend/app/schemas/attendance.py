import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.attendance_session import AttendanceSession, SessionStatus
from app.schemas.academic import SubjectBrief


class SessionCreateRequest(BaseModel):
    class_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    latitude: float
    longitude: float
    radius_meters: float


class SessionCreateResponse(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    status: SessionStatus
    starts_at: datetime
    ends_at: datetime

    model_config = {"from_attributes": True}


class SessionEndResponse(BaseModel):
    id: uuid.UUID
    status: SessionStatus
    ended_at: datetime

    model_config = {"from_attributes": True}


class ClassBrief(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class FacultyBrief(BaseModel):
    id: uuid.UUID
    name: str


class FacultyNameOnly(BaseModel):
    name: str


class SessionDetailResponse(BaseModel):
    """Shape for GET /attendance/sessions/{id} (docs/API.md §19). Built via
    `from_session`, not straight `from_attributes`, because `faculty.name`
    isn't a column (it lives on the related User) and `class` is a reserved
    word Python can't use as a plain attribute name.
    """

    id: uuid.UUID
    class_: ClassBrief = Field(serialization_alias="class")
    subject: SubjectBrief
    faculty: FacultyBrief
    starts_at: datetime
    ends_at: datetime
    status: SessionStatus

    @classmethod
    def from_session(cls, session: AttendanceSession) -> "SessionDetailResponse":
        return cls(
            id=session.id,
            class_=ClassBrief.model_validate(session.class_offering),
            subject=SubjectBrief.model_validate(session.class_offering.subject),
            faculty=FacultyBrief(id=session.faculty.id, name=session.faculty.user.name),
            starts_at=session.starts_at,
            ends_at=session.ends_at,
            status=session.status,
        )


class ActiveSessionItem(BaseModel):
    """Shape for one item of GET /attendance/sessions/active (docs/API.md
    §18) — faculty is name-only there, unlike the detail endpoint.
    """

    id: uuid.UUID
    class_: ClassBrief = Field(serialization_alias="class")
    subject: SubjectBrief
    faculty: FacultyNameOnly
    starts_at: datetime
    ends_at: datetime

    @classmethod
    def from_session(cls, session: AttendanceSession) -> "ActiveSessionItem":
        return cls(
            id=session.id,
            class_=ClassBrief.model_validate(session.class_offering),
            subject=SubjectBrief.model_validate(session.class_offering.subject),
            faculty=FacultyNameOnly(name=session.faculty.user.name),
            starts_at=session.starts_at,
            ends_at=session.ends_at,
        )


class ActiveSessionListResponse(BaseModel):
    items: list[ActiveSessionItem]


class FacultySessionListResponse(BaseModel):
    items: list[SessionDetailResponse]


RosterStatus = Literal["PRESENT", "NOT_MARKED", "VERIFICATION_ISSUE"]


class RosterSessionBrief(BaseModel):
    """`status` isn't in docs/API.md §24's example, but the frontend needs
    it to tell an active session's roster (poll, show LIVE) apart from a
    past one's (static, no LIVE badge) — same "small, deliberate addition"
    precedent as `AttendanceSession.ended_at` in Phase 4.
    """

    id: uuid.UUID
    class_name: str
    subject: str
    status: SessionStatus


class RosterSummary(BaseModel):
    total_students: int
    present: int
    not_marked: int
    verification_issues: int


class RosterStudentItem(BaseModel):
    """`status` isn't a persisted column anywhere — it's computed per
    roster request from whether an `Attendance` row exists (`PRESENT`) or
    an `AttendanceVerification` attempt was ever started (`VERIFICATION_
    ISSUE`, meaning tried and didn't finish) or neither (`NOT_MARKED`).
    """

    student_id: uuid.UUID
    name: str
    prn: str
    status: RosterStatus
    marked_at: datetime | None = None


class SessionRosterResponse(BaseModel):
    """docs/API.md §24. `class_name`/`subject` are flat strings here,
    unlike `SessionDetailResponse`'s nested objects — matches the doc's own
    example exactly rather than reusing that shape for consistency's sake.
    """

    session: RosterSessionBrief
    summary: RosterSummary
    students: list[RosterStudentItem]
