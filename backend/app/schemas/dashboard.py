from pydantic import BaseModel

from app.schemas.attendance import ActiveSessionItem, SessionDetailResponse


class StudentBrief(BaseModel):
    name: str


class AttendanceOverview(BaseModel):
    percentage: float
    present: int
    total: int


class StudentDashboardResponse(BaseModel):
    """docs/API.md §11. `today_classes` has no documented item shape (the
    example shows an empty list) — reuses `ActiveSessionItem` since it's
    already the student-facing "brief session" shape, rather than
    inventing a near-duplicate one.
    """

    student: StudentBrief
    attendance: AttendanceOverview
    active_session: ActiveSessionItem | None = None
    today_classes: list[ActiveSessionItem]


class TodaySummary(BaseModel):
    classes: int
    active_sessions: int
    upcoming_sessions: int


class FacultyDashboardResponse(BaseModel):
    """docs/API.md §43. `active_session`/`upcoming_classes` reuse
    `SessionDetailResponse` (the faculty-facing "session with full nested
    class/subject/faculty" shape already used by `GET
    /attendance/sessions/{id}`) for the same reason.
    """

    today: TodaySummary
    active_session: SessionDetailResponse | None = None
    upcoming_classes: list[SessionDetailResponse]
