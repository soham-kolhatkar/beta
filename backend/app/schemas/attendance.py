import uuid
from datetime import datetime

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
