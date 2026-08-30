"""Integration tests for the student and faculty dashboard endpoints
(Phase 6a): GET /students/me/dashboard, GET /faculty/me/dashboard. Real
routing, real Postgres via the transactional-rollback fixture — see
test_auth.py's docstring for why this tier vs. a unit test.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import face_model
from app.models.user import UserRole
from app.services import face_service
from tests.factories import (
    create_academic_context,
    create_class_offering,
    create_enrollment,
    create_face_profile,
    create_faculty,
    create_student,
    create_user,
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


async def _setup(client: AsyncClient, db_session: AsyncSession) -> dict[str, Any]:
    institution, academic_year, branch, division = await create_academic_context(db_session)
    _, faculty = await create_faculty(db_session)
    _, student = await create_student(db_session, branch, division, academic_year)
    class_offering = await create_class_offering(
        db_session, institution, faculty, division, academic_year
    )
    await create_enrollment(db_session, class_offering, student)
    await db_session.commit()

    return {"class_id": str(class_offering.id), "student": student, "faculty": faculty}


async def _create_session(client: AsyncClient, class_id: str, **overrides: Any) -> str:
    await login(client, "test-faculty@example.com", "password123")
    response = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(class_id, **overrides)
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _complete_attendance(
    client: AsyncClient, db_session: AsyncSession, student, session_id: str
) -> None:
    image = face_service.decode_image("image/jpeg", FIXTURE_FACE)
    embedding = face_model.extract_embedding(image)
    await create_face_profile(db_session, student, embedding=embedding)
    await db_session.commit()

    await login(client, "test-student@example.com", "password123")
    start = await client.post(f"/api/v1/attendance/sessions/{session_id}/verification")
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


async def test_student_dashboard_zero_attendance_with_no_history(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _setup(client, db_session)
    await login(client, "test-student@example.com", "password123")

    response = await client.get("/api/v1/students/me/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["attendance"] == {"percentage": 0.0, "present": 0, "total": 0}
    assert body["active_session"] is None
    assert body["today_classes"] == []


async def test_student_dashboard_full_percentage_after_marking_and_ending(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    session_id = await _create_session(client, ctx["class_id"])
    await _complete_attendance(client, db_session, ctx["student"], session_id)

    await login(client, "test-faculty@example.com", "password123")
    end_response = await client.post(f"/api/v1/attendance/sessions/{session_id}/end")
    assert end_response.status_code == 200

    await login(client, "test-student@example.com", "password123")
    response = await client.get("/api/v1/students/me/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["attendance"] == {"percentage": 100.0, "present": 1, "total": 1}


async def test_student_dashboard_shows_active_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    session_id = await _create_session(client, ctx["class_id"])

    await login(client, "test-student@example.com", "password123")
    response = await client.get("/api/v1/students/me/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["active_session"] is not None
    assert body["active_session"]["id"] == session_id


async def test_student_dashboard_shows_todays_class(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    session_id = await _create_session(client, ctx["class_id"])

    await login(client, "test-student@example.com", "password123")
    response = await client.get("/api/v1/students/me/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == session_id for item in body["today_classes"])


async def test_student_dashboard_requires_student_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "test-admin@example.com", "password123", UserRole.ADMIN)
    await db_session.commit()
    await login(client, "test-admin@example.com", "password123")

    response = await client.get("/api/v1/students/me/dashboard")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


async def test_student_dashboard_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/students/me/dashboard")
    assert response.status_code == 401


async def test_faculty_dashboard_empty_with_no_sessions_today(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _setup(client, db_session)
    await login(client, "test-faculty@example.com", "password123")

    response = await client.get("/api/v1/faculty/me/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["today"] == {"classes": 0, "active_sessions": 0, "upcoming_sessions": 0}
    assert body["active_session"] is None
    assert body["upcoming_classes"] == []


async def test_faculty_dashboard_counts_active_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    session_id = await _create_session(client, ctx["class_id"])

    response = await client.get("/api/v1/faculty/me/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["today"]["classes"] == 1
    assert body["today"]["active_sessions"] == 1
    assert body["today"]["upcoming_sessions"] == 0
    assert body["active_session"]["id"] == session_id


async def test_faculty_dashboard_counts_upcoming_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    now = datetime.now(timezone.utc)
    session_id = await _create_session(
        client,
        ctx["class_id"],
        starts_at=_iso(now + timedelta(hours=2)),
        ends_at=_iso(now + timedelta(hours=3)),
    )

    response = await client.get("/api/v1/faculty/me/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["today"]["classes"] == 1
    assert body["today"]["active_sessions"] == 0
    assert body["today"]["upcoming_sessions"] == 1
    assert body["active_session"] is None
    assert any(item["id"] == session_id for item in body["upcoming_classes"])


async def test_faculty_dashboard_requires_faculty_role(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _setup(client, db_session)
    await login(client, "test-student@example.com", "password123")

    response = await client.get("/api/v1/faculty/me/dashboard")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_faculty_dashboard_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/faculty/me/dashboard")
    assert response.status_code == 401
