import math
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.models.attendance import AttendanceStatus
from app.models.student import Student
from app.models.user import User
from app.repositories import (
    attendance_repository,
    attendance_session_repository,
    class_enrollment_repository,
    class_offering_repository,
    student_repository,
)
from app.schemas.attendance import ActiveSessionItem
from app.schemas.dashboard import AttendanceOverview, StudentBrief, StudentDashboardResponse
from app.schemas.history import (
    AttendanceHistoryItem,
    AttendanceHistoryResponse,
    AttendanceSummaryResponse,
    ClassAttendanceClassBrief,
    ClassAttendanceResponse,
    PaginationInfo,
    SubjectAttendanceSummary,
)


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


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise ApiError("INVALID_REQUEST", "page must be at least 1.", status_code=422)
    if not (1 <= page_size <= 100):
        raise ApiError("INVALID_REQUEST", "page_size must be between 1 and 100.", status_code=422)


async def get_attendance_history(
    db: AsyncSession,
    student: Student,
    *,
    subject_id: uuid.UUID | None,
    status: AttendanceStatus | None,
    from_date: date | None,
    to_date: date | None,
    page: int,
    page_size: int,
) -> AttendanceHistoryResponse:
    _validate_pagination(page, page_size)

    from_dt = datetime.combine(from_date, time.min, tzinfo=timezone.utc) if from_date else None
    to_dt = (
        datetime.combine(to_date, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        if to_date
        else None
    )

    items, total = await attendance_repository.list_for_student(
        db,
        student.id,
        subject_id=subject_id,
        status=status,
        from_dt=from_dt,
        to_dt=to_dt,
        page=page,
        page_size=page_size,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return AttendanceHistoryResponse(
        items=[AttendanceHistoryItem.from_attendance(a) for a in items],
        pagination=PaginationInfo(
            page=page, page_size=page_size, total=total, total_pages=total_pages
        ),
    )


async def get_attendance_summary(db: AsyncSession, student: Student) -> AttendanceSummaryResponse:
    now = datetime.now(timezone.utc)

    total = await attendance_repository.count_ended_sessions_for_student(db, student.id, now)
    present = await attendance_repository.count_by_student(db, student.id)
    overall_percentage = round((present / total) * 100, 1) if total > 0 else 0.0

    classes = await class_enrollment_repository.list_classes_for_student(db, student.id)
    class_ids = [c.id for c in classes]
    present_by_class = await attendance_repository.count_present_by_class_for_student(
        db, student.id, class_ids
    )
    ended_by_class = await attendance_session_repository.count_ended_by_class_ids(
        db, class_ids, now
    )

    subjects = []
    for class_offering in classes:
        class_present = present_by_class.get(class_offering.id, 0)
        class_total = ended_by_class.get(class_offering.id, 0)
        class_percentage = round((class_present / class_total) * 100, 1) if class_total > 0 else 0.0
        subjects.append(
            SubjectAttendanceSummary(
                class_id=class_offering.id,
                subject=class_offering.subject.name,
                percentage=class_percentage,
                present=class_present,
                total=class_total,
            )
        )

    return AttendanceSummaryResponse(
        overall=AttendanceOverview(percentage=overall_percentage, present=present, total=total),
        subjects=subjects,
    )


async def get_class_attendance(
    db: AsyncSession, student: Student, class_id: uuid.UUID
) -> ClassAttendanceResponse:
    class_offering = await class_offering_repository.get_by_id_with_subject(db, class_id)
    if class_offering is None:
        raise ApiError("RESOURCE_NOT_FOUND", "Class not found.", status_code=404)

    enrollment = await class_enrollment_repository.get_by_class_and_student(
        db, class_id, student.id
    )
    if enrollment is None:
        raise ApiError("FORBIDDEN", "You are not enrolled in this class.", status_code=403)

    now = datetime.now(timezone.utc)
    present_by_class = await attendance_repository.count_present_by_class_for_student(
        db, student.id, [class_id]
    )
    ended_by_class = await attendance_session_repository.count_ended_by_class_ids(
        db, [class_id], now
    )
    present = present_by_class.get(class_id, 0)
    total = ended_by_class.get(class_id, 0)
    percentage = round((present / total) * 100, 1) if total > 0 else 0.0

    records = await attendance_repository.list_for_student_and_class(db, student.id, class_id)

    return ClassAttendanceResponse(
        class_=ClassAttendanceClassBrief(id=class_offering.id, subject=class_offering.subject.name),
        summary=AttendanceOverview(percentage=percentage, present=present, total=total),
        records=[AttendanceHistoryItem.from_attendance(a) for a in records],
    )
