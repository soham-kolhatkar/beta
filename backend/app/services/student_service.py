from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.student import Student
from app.models.user import User
from app.repositories import (
    attendance_repository,
    attendance_session_repository,
    student_repository,
)
from app.schemas.attendance import ActiveSessionItem
from app.schemas.dashboard import AttendanceOverview, StudentBrief, StudentDashboardResponse


async def get_my_profile(db: AsyncSession, user: User) -> Student:
    student = await student_repository.get_by_user_id(db, user.id)
    if student is None:
        raise ApiError(
            "RESOURCE_NOT_FOUND", "No student profile exists for this account.", status_code=404
        )
    return student


async def get_dashboard(db: AsyncSession, student: Student) -> StudentDashboardResponse:
    now = datetime.now(timezone.utc)

    total = await attendance_repository.count_ended_sessions_for_student(db, student.id, now)
    present = await attendance_repository.count_by_student(db, student.id)
    percentage = round((present / total) * 100, 1) if total > 0 else 0.0

    active_sessions = await attendance_session_repository.list_active_for_student(
        db, student.id, now
    )
    active_session = ActiveSessionItem.from_session(active_sessions[0]) if active_sessions else None

    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    today_sessions = await attendance_session_repository.list_for_student_between(
        db, student.id, day_start, day_end
    )

    return StudentDashboardResponse(
        student=StudentBrief(name=student.user.name),
        attendance=AttendanceOverview(percentage=percentage, present=present, total=total),
        active_session=active_session,
        today_classes=[ActiveSessionItem.from_session(s) for s in today_sessions],
    )
