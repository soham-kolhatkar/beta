import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.attendance import Attendance, AttendanceStatus
from app.schemas.dashboard import AttendanceOverview


class PaginationInfo(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class AttendanceHistoryItem(BaseModel):
    """docs/API.md §14. `subject` is a flat name string, matching the doc's
    own example, not the nested `SubjectBrief` used elsewhere.
    """

    id: uuid.UUID
    session_id: uuid.UUID
    subject: str
    marked_at: datetime
    status: AttendanceStatus

    @classmethod
    def from_attendance(cls, attendance: Attendance) -> "AttendanceHistoryItem":
        return cls(
            id=attendance.id,
            session_id=attendance.session_id,
            subject=attendance.session.class_offering.subject.name,
            marked_at=attendance.marked_at,
            status=attendance.status,
        )


class AttendanceHistoryResponse(BaseModel):
    items: list[AttendanceHistoryItem]
    pagination: PaginationInfo


class SubjectAttendanceSummary(BaseModel):
    class_id: uuid.UUID
    subject: str
    percentage: float
    present: int
    total: int


class AttendanceSummaryResponse(BaseModel):
    """docs/API.md §13. `overall` reuses `AttendanceOverview` (already the
    dashboard's "percentage/present/total" shape) rather than a duplicate.
    """

    overall: AttendanceOverview
    subjects: list[SubjectAttendanceSummary]


class ClassAttendanceClassBrief(BaseModel):
    id: uuid.UUID
    subject: str


class ClassAttendanceResponse(BaseModel):
    """docs/API.md §15."""

    class_: ClassAttendanceClassBrief = Field(serialization_alias="class")
    summary: AttendanceOverview
    records: list[AttendanceHistoryItem]
