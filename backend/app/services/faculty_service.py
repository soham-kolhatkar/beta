from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.attendance_session import SessionStatus
from app.models.class_offering import ClassOffering
from app.models.faculty import Faculty
from app.models.user import User
from app.repositories import (
    attendance_session_repository,
    class_enrollment_repository,
    class_offering_repository,
    faculty_repository,
)
from app.schemas.attendance import SessionDetailResponse
from app.schemas.dashboard import FacultyDashboardResponse, TodaySummary


async def get_my_profile(db: AsyncSession, user: User) -> Faculty:
    faculty = await faculty_repository.get_by_user_id(db, user.id)
    if faculty is None:
        raise ApiError(
            "RESOURCE_NOT_FOUND", "No faculty profile exists for this account.", status_code=404
        )
    return faculty


async def list_my_classes(db: AsyncSession, faculty: Faculty) -> list[tuple[ClassOffering, int]]:
    classes = await class_offering_repository.list_for_faculty(db, faculty.id)
    counts = await class_enrollment_repository.count_by_class_ids(db, [c.id for c in classes])
    return [(c, counts.get(c.id, 0)) for c in classes]


async def get_dashboard(db: AsyncSession, faculty: Faculty) -> FacultyDashboardResponse:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    today_sessions = await attendance_session_repository.list_for_faculty_between(
        db, faculty.id, day_start, day_end
    )

    active_today = [
        s
        for s in today_sessions
        if s.status == SessionStatus.ACTIVE and s.starts_at <= now <= s.ends_at
    ]
    upcoming_today = [s for s in today_sessions if s.starts_at > now]

    active_session = SessionDetailResponse.from_session(active_today[0]) if active_today else None

    return FacultyDashboardResponse(
        today=TodaySummary(
            classes=len(today_sessions),
            active_sessions=len(active_today),
            upcoming_sessions=len(upcoming_today),
        ),
        active_session=active_session,
        upcoming_classes=[SessionDetailResponse.from_session(s) for s in upcoming_today],
    )
