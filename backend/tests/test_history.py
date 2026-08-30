"""Integration tests for Phase 6b's history endpoints:
GET /students/me/attendance, GET /students/me/attendance/summary,
GET /students/me/classes/{class_id}/attendance. Real routing, real
Postgres via the transactional-rollback fixture — see test_auth.py's
docstring for why this tier vs. a unit test.

Sessions here are backdated (ended days ago), which the real
POST /attendance/sessions endpoint can't produce (it only accepts a
currently-valid time window) — so, like scripts/seed.py, these are
inserted directly via the ORM rather than through the API.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance import Attendance
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.class_offering import ClassOffering
from app.models.student import Student
from tests.factories import (
    create_academic_context,
    create_class_offering,
    create_enrollment,
    create_faculty,
    create_student,
    login,
)

SESSION_LAT = 18.5204
SESSION_LON = 73.8567
SESSION_RADIUS = 100.0


async def _create_ended_session(
    db_session: AsyncSession,
    class_offering: ClassOffering,
    student: Student,
    *,
    days_ago: int,
    present: bool,
) -> AttendanceSession:
    starts_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    ends_at = starts_at + timedelta(hours=1)

    session = AttendanceSession(
        class_id=class_offering.id,
        faculty_id=class_offering.faculty_id,
        latitude=SESSION_LAT,
        longitude=SESSION_LON,
        radius_meters=SESSION_RADIUS,
        starts_at=starts_at,
        ends_at=ends_at,
        status=SessionStatus.ENDED,
        ended_at=ends_at,
    )
    db_session.add(session)
    await db_session.flush()

    if present:
        db_session.add(
            Attendance(
                session_id=session.id,
                student_id=student.id,
                marked_at=starts_at + timedelta(minutes=5),
                latitude=SESSION_LAT,
                longitude=SESSION_LON,
                location_accuracy=10.0,
                distance_meters=5.0,
                face_verified=True,
                face_score=0.15,
            )
        )
    await db_session.flush()
    return session


async def _setup_two_classes(client: AsyncClient, db_session: AsyncSession) -> dict[str, Any]:
    institution, academic_year, branch, division = await create_academic_context(db_session)
    _, faculty = await create_faculty(db_session)
    _, student = await create_student(db_session, branch, division, academic_year)

    dbms = await create_class_offering(
        db_session, institution, faculty, division, academic_year, subject_code="DBMS", name="DBMS"
    )
    os_class = await create_class_offering(
        db_session, institution, faculty, division, academic_year, subject_code="OS", name="OS"
    )
    await create_enrollment(db_session, dbms, student)
    await create_enrollment(db_session, os_class, student)
    await db_session.commit()

    return {
        "student": student,
        "faculty": faculty,
        "dbms": dbms,
        "os": os_class,
        "institution": institution,
        "academic_year": academic_year,
        "branch": branch,
        "division": division,
    }


async def test_history_returns_items_with_pagination(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup_two_classes(client, db_session)
    for i in range(3):
        await _create_ended_session(
            db_session, ctx["dbms"], ctx["student"], days_ago=i + 1, present=True
        )
    await _create_ended_session(db_session, ctx["dbms"], ctx["student"], days_ago=4, present=False)
    await db_session.commit()

    await login(client, "test-student@example.com", "password123")

    page1 = await client.get("/api/v1/students/me/attendance?page=1&page_size=2")
    assert page1.status_code == 200
    body1 = page1.json()
    assert len(body1["items"]) == 2
    assert body1["pagination"] == {"page": 1, "page_size": 2, "total": 3, "total_pages": 2}
    # Most recent first.
    assert body1["items"][0]["marked_at"] > body1["items"][1]["marked_at"]

    page2 = await client.get("/api/v1/students/me/attendance?page=2&page_size=2")
    assert len(page2.json()["items"]) == 1


async def test_history_filters_by_subject_id(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup_two_classes(client, db_session)
    await _create_ended_session(db_session, ctx["dbms"], ctx["student"], days_ago=1, present=True)
    await _create_ended_session(db_session, ctx["os"], ctx["student"], days_ago=1, present=True)
    await db_session.commit()

    await login(client, "test-student@example.com", "password123")
    response = await client.get(
        f"/api/v1/students/me/attendance?subject_id={ctx['dbms'].subject_id}"
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["subject"] == "Test Subject"


async def test_history_filters_by_date_range(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup_two_classes(client, db_session)
    await _create_ended_session(db_session, ctx["dbms"], ctx["student"], days_ago=1, present=True)
    await _create_ended_session(db_session, ctx["dbms"], ctx["student"], days_ago=10, present=True)
    await db_session.commit()

    await login(client, "test-student@example.com", "password123")
    today = datetime.now(timezone.utc).date()
    response = await client.get(
        f"/api/v1/students/me/attendance?from={today - timedelta(days=2)}&to={today}"
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


async def test_history_rejects_page_size_over_max(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _setup_two_classes(client, db_session)
    await login(client, "test-student@example.com", "password123")

    response = await client.get("/api/v1/students/me/attendance?page_size=200")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


async def test_history_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/students/me/attendance")
    assert response.status_code == 401


async def test_summary_zero_state_for_enrolled_classes_with_no_sessions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _setup_two_classes(client, db_session)
    await login(client, "test-student@example.com", "password123")

    response = await client.get("/api/v1/students/me/attendance/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["overall"] == {"percentage": 0.0, "present": 0, "total": 0}
    assert len(body["subjects"]) == 2
    assert all(s["total"] == 0 and s["percentage"] == 0.0 for s in body["subjects"])


async def test_summary_computes_overall_and_per_subject_percentages(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup_two_classes(client, db_session)
    # DBMS: 1 present out of 2 ended sessions (50%).
    await _create_ended_session(db_session, ctx["dbms"], ctx["student"], days_ago=1, present=True)
    await _create_ended_session(db_session, ctx["dbms"], ctx["student"], days_ago=2, present=False)
    # OS: 2 present out of 2 ended sessions (100%).
    await _create_ended_session(db_session, ctx["os"], ctx["student"], days_ago=1, present=True)
    await _create_ended_session(db_session, ctx["os"], ctx["student"], days_ago=2, present=True)
    await db_session.commit()

    await login(client, "test-student@example.com", "password123")
    response = await client.get("/api/v1/students/me/attendance/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["overall"] == {"percentage": 75.0, "present": 3, "total": 4}
    by_class = {s["class_id"]: s for s in body["subjects"]}
    assert by_class[str(ctx["dbms"].id)]["percentage"] == 50.0
    assert by_class[str(ctx["os"].id)]["percentage"] == 100.0


async def test_summary_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/students/me/attendance/summary")
    assert response.status_code == 401


async def test_class_attendance_returns_summary_and_records(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup_two_classes(client, db_session)
    await _create_ended_session(db_session, ctx["dbms"], ctx["student"], days_ago=1, present=True)
    await _create_ended_session(db_session, ctx["dbms"], ctx["student"], days_ago=2, present=False)
    await db_session.commit()

    await login(client, "test-student@example.com", "password123")
    response = await client.get(f"/api/v1/students/me/classes/{ctx['dbms'].id}/attendance")

    assert response.status_code == 200
    body = response.json()
    assert body["class"] == {"id": str(ctx["dbms"].id), "subject": "Test Subject"}
    assert body["summary"] == {"percentage": 50.0, "present": 1, "total": 2}
    assert len(body["records"]) == 1


async def test_class_attendance_rejects_unenrolled_student(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup_two_classes(client, db_session)
    other_class = await create_class_offering(
        db_session,
        ctx["institution"],
        ctx["faculty"],
        ctx["division"],
        ctx["academic_year"],
        subject_code="AI",
        name="AI",
    )
    await db_session.commit()

    await login(client, "test-student@example.com", "password123")
    response = await client.get(f"/api/v1/students/me/classes/{other_class.id}/attendance")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_class_attendance_not_found(client: AsyncClient, db_session: AsyncSession) -> None:
    await _setup_two_classes(client, db_session)
    await login(client, "test-student@example.com", "password123")

    response = await client.get(
        "/api/v1/students/me/classes/00000000-0000-0000-0000-000000000000/attendance"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


async def test_class_attendance_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/students/me/classes/00000000-0000-0000-0000-000000000000/attendance"
    )
    assert response.status_code == 401


async def test_history_does_not_leak_another_students_attendance(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """The API has no student_id path/query parameter anywhere in this
    surface — every endpoint derives the student from the session cookie —
    so cross-user access is prevented by construction. This proves it: a
    second student with real attendance data sees none of it reflected in
    their own history/summary, and vice versa.
    """
    ctx = await _setup_two_classes(client, db_session)
    _, other_student = await create_student(
        db_session,
        ctx["branch"],
        ctx["division"],
        ctx["academic_year"],
        email="test-student-2@example.com",
        prn="STU-9002",
    )
    await create_enrollment(db_session, ctx["dbms"], other_student)
    await _create_ended_session(db_session, ctx["dbms"], ctx["student"], days_ago=1, present=True)
    await db_session.commit()

    await login(client, "test-student-2@example.com", "password123")
    response = await client.get("/api/v1/students/me/attendance")

    assert response.status_code == 200
    assert response.json()["items"] == []

    # `total` (1) correctly reflects a countable ended session for a class
    # they're enrolled in — that isn't a leak. `present` (0) is what proves
    # they don't inherit the other student's attendance record.
    summary = await client.get("/api/v1/students/me/attendance/summary")
    assert summary.json()["overall"] == {"percentage": 0.0, "present": 0, "total": 1}
