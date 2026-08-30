"""Integration tests for the faculty live roster (Phase 6a):
GET /attendance/sessions/{id}/attendance. Real routing, real Postgres via
the transactional-rollback fixture — see test_auth.py's docstring for why
this tier vs. a unit test.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import face_model
from app.services import face_service
from tests.factories import (
    create_academic_context,
    create_class_offering,
    create_enrollment,
    create_face_profile,
    create_faculty,
    create_student,
    login,
)

FIXTURE_FACE = (Path(__file__).parent / "fixtures" / "face.jpg").read_bytes()

SESSION_LAT = 18.5204
SESSION_LON = 73.8567
SESSION_RADIUS = 100


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _session_payload(class_id: str, **overrides: Any) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    payload = {
        "class_id": class_id,
        "starts_at": _iso(now - timedelta(minutes=5)),
        "ends_at": _iso(now + timedelta(hours=1)),
        "latitude": SESSION_LAT,
        "longitude": SESSION_LON,
        "radius_meters": SESSION_RADIUS,
    }
    payload.update(overrides)
    return payload


async def _setup_with_two_students(client: AsyncClient, db_session: AsyncSession) -> dict[str, Any]:
    """Faculty owning one class, two enrolled students (neither
    face-registered yet), one currently-active session for that class.
    """
    institution, academic_year, branch, division = await create_academic_context(db_session)
    _, faculty = await create_faculty(db_session)
    _, student_a = await create_student(
        db_session,
        branch,
        division,
        academic_year,
        email="test-student-a@example.com",
        prn="STU-A",
    )
    _, student_b = await create_student(
        db_session,
        branch,
        division,
        academic_year,
        email="test-student-b@example.com",
        prn="STU-B",
    )
    class_offering = await create_class_offering(
        db_session, institution, faculty, division, academic_year
    )
    await create_enrollment(db_session, class_offering, student_a)
    await create_enrollment(db_session, class_offering, student_b)
    await db_session.commit()

    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(str(class_offering.id))
    )
    assert created.status_code == 201

    return {
        "session_id": created.json()["id"],
        "student_a": student_a,
        "student_b": student_b,
    }


async def test_roster_not_marked_for_untouched_student(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup_with_two_students(client, db_session)

    response = await client.get(f"/api/v1/attendance/sessions/{ctx['session_id']}/attendance")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_students"] == 2
    assert body["summary"]["not_marked"] == 2
    assert body["summary"]["present"] == 0
    assert body["summary"]["verification_issues"] == 0
    statuses = {item["prn"]: item["status"] for item in body["students"]}
    assert statuses == {"STU-A": "NOT_MARKED", "STU-B": "NOT_MARKED"}


async def test_roster_verification_issue_for_incomplete_attempt(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup_with_two_students(client, db_session)

    # A student needs a registered face just to start a verification
    # attempt at all (docs/API.md §27) — the embedding itself doesn't need
    # to match anything for this test, since the attempt is deliberately
    # left incomplete (no location/face submitted).
    await create_face_profile(db_session, ctx["student_a"])
    await db_session.commit()

    await login(client, "test-student-a@example.com", "password123")
    start = await client.post(f"/api/v1/attendance/sessions/{ctx['session_id']}/verification")
    assert start.status_code == 200

    await login(client, "test-faculty@example.com", "password123")
    response = await client.get(f"/api/v1/attendance/sessions/{ctx['session_id']}/attendance")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["verification_issues"] == 1
    assert body["summary"]["not_marked"] == 1
    statuses = {item["prn"]: item["status"] for item in body["students"]}
    assert statuses["STU-A"] == "VERIFICATION_ISSUE"
    assert statuses["STU-B"] == "NOT_MARKED"


async def test_roster_present_after_full_flow(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup_with_two_students(client, db_session)

    # Use the real fixture embedding so a live submission of the same image
    # actually matches.
    image = face_service.decode_image("image/jpeg", FIXTURE_FACE)
    embedding = face_model.extract_embedding(image)
    await create_face_profile(db_session, ctx["student_a"], embedding=embedding)
    await db_session.commit()

    await login(client, "test-student-a@example.com", "password123")
    start = await client.post(f"/api/v1/attendance/sessions/{ctx['session_id']}/verification")
    verification_id = start.json()["verification_id"]
    await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )
    await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/face",
        files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")},
    )
    complete = await client.post(f"/api/v1/attendance/verifications/{verification_id}/complete")
    assert complete.status_code == 200

    await login(client, "test-faculty@example.com", "password123")
    response = await client.get(f"/api/v1/attendance/sessions/{ctx['session_id']}/attendance")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["present"] == 1
    assert body["summary"]["not_marked"] == 1
    student_a_item = next(item for item in body["students"] if item["prn"] == "STU-A")
    assert student_a_item["status"] == "PRESENT"
    assert student_a_item["marked_at"] is not None


async def test_roster_rejects_other_faculty(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup_with_two_students(client, db_session)

    await create_faculty(db_session, email="test-faculty2@example.com", employee_id="EMP-9002")
    await db_session.commit()
    await login(client, "test-faculty2@example.com", "password123")

    response = await client.get(f"/api/v1/attendance/sessions/{ctx['session_id']}/attendance")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_roster_not_found(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_faculty(db_session)
    await db_session.commit()
    await login(client, "test-faculty@example.com", "password123")

    response = await client.get(
        "/api/v1/attendance/sessions/00000000-0000-0000-0000-000000000000/attendance"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"


async def test_roster_requires_faculty_role(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup_with_two_students(client, db_session)
    await login(client, "test-student-a@example.com", "password123")

    response = await client.get(f"/api/v1/attendance/sessions/{ctx['session_id']}/attendance")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_roster_requires_authentication(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/attendance/sessions/00000000-0000-0000-0000-000000000000/attendance"
    )
    assert response.status_code == 401
