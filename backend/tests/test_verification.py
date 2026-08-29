"""Integration tests for the verification-context flow (Phase 5a):
POST /attendance/sessions/{id}/verification, POST
/attendance/verifications/{id}/location. Real routing, real Postgres via
the transactional-rollback fixture — see test_auth.py's docstring for why
this tier vs. a unit test. Sessions are created/ended through the real
Phase 4 endpoints rather than inserted directly, for the same reason;
only states nothing else can produce yet (an expired verification
context, an already-FACE_VERIFIED one) are set via direct DB writes.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_verification import AttendanceVerification, VerificationStatus
from tests.factories import (
    create_academic_context,
    create_class_offering,
    create_enrollment,
    create_face_profile,
    create_faculty,
    create_student,
    login,
)

SESSION_LAT = 18.5204
SESSION_LON = 73.8567
SESSION_RADIUS = 100

# ~222m north of the session's coordinates — well outside a 100m radius.
FAR_LAT = SESSION_LAT + 0.002


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


async def _setup(
    client: AsyncClient, db_session: AsyncSession, *, face_registered: bool = True
) -> dict[str, Any]:
    """Faculty owning one class, one enrolled student (face-registered by
    default), one currently-active session for that class.
    """
    institution, academic_year, branch, division = await create_academic_context(db_session)
    _, faculty = await create_faculty(db_session)
    _, student = await create_student(db_session, branch, division, academic_year)
    class_offering = await create_class_offering(
        db_session, institution, faculty, division, academic_year
    )
    await create_enrollment(db_session, class_offering, student)
    if face_registered:
        await create_face_profile(db_session, student)
    await db_session.commit()

    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(str(class_offering.id))
    )
    assert created.status_code == 201

    return {
        "institution": institution,
        "academic_year": academic_year,
        "branch": branch,
        "division": division,
        "class_id": str(class_offering.id),
        "session_id": created.json()["id"],
        "student": student,
    }


async def _start_verification(client: AsyncClient, session_id: str) -> str:
    await login(client, "test-student@example.com", "password123")
    response = await client.post(f"/api/v1/attendance/sessions/{session_id}/verification")
    assert response.status_code == 200
    return response.json()["verification_id"]


async def test_start_verification_success(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup(client, db_session)
    await login(client, "test-student@example.com", "password123")

    response = await client.post(f"/api/v1/attendance/sessions/{ctx['session_id']}/verification")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == ctx["session_id"]
    assert body["steps"] == ["LOCATION", "FACE"]
    assert "verification_id" in body


async def test_start_verification_rejects_unenrolled_student(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await create_student(
        db_session,
        ctx["branch"],
        ctx["division"],
        ctx["academic_year"],
        email="test-student-other@example.com",
        prn="STU-9002",
    )
    await db_session.commit()
    await login(client, "test-student-other@example.com", "password123")

    response = await client.post(f"/api/v1/attendance/sessions/{ctx['session_id']}/verification")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_ENROLLED"


async def test_start_verification_rejects_no_face_registered(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session, face_registered=False)
    await login(client, "test-student@example.com", "password123")

    response = await client.post(f"/api/v1/attendance/sessions/{ctx['session_id']}/verification")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FACE_NOT_REGISTERED"


async def test_start_verification_rejects_session_not_started(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    institution, academic_year, branch, division = await create_academic_context(db_session)
    _, faculty = await create_faculty(db_session)
    _, student = await create_student(db_session, branch, division, academic_year)
    class_offering = await create_class_offering(
        db_session, institution, faculty, division, academic_year
    )
    await create_enrollment(db_session, class_offering, student)
    await create_face_profile(db_session, student)
    await db_session.commit()

    await login(client, "test-faculty@example.com", "password123")
    now = datetime.now(timezone.utc)
    created = await client.post(
        "/api/v1/attendance/sessions",
        json=_session_payload(
            str(class_offering.id),
            starts_at=_iso(now + timedelta(hours=1)),
            ends_at=_iso(now + timedelta(hours=2)),
        ),
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    await login(client, "test-student@example.com", "password123")
    response = await client.post(f"/api/v1/attendance/sessions/{session_id}/verification")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SESSION_NOT_ACTIVE"


async def test_start_verification_rejects_ended_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await login(client, "test-faculty@example.com", "password123")
    end_response = await client.post(f"/api/v1/attendance/sessions/{ctx['session_id']}/end")
    assert end_response.status_code == 200

    await login(client, "test-student@example.com", "password123")
    response = await client.post(f"/api/v1/attendance/sessions/{ctx['session_id']}/verification")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"


async def test_start_verification_session_not_found(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, academic_year, branch, division = await create_academic_context(db_session)
    await create_student(db_session, branch, division, academic_year)
    await db_session.commit()
    await login(client, "test-student@example.com", "password123")

    response = await client.post(
        "/api/v1/attendance/sessions/00000000-0000-0000-0000-000000000000/verification"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"


async def test_start_verification_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/attendance/sessions/00000000-0000-0000-0000-000000000000/verification"
    )
    assert response.status_code == 401


async def test_submit_location_success_within_radius(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_verification(client, ctx["session_id"])

    response = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert body["next_step"] == "FACE"
    assert body["distance_meters"] < 1
    assert "code" not in body
    assert "message" not in body
    assert "allowed_radius_meters" not in body


async def test_submit_location_rejects_outside_radius(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_verification(client, ctx["session_id"])

    response = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": FAR_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is False
    assert body["code"] == "LOCATION_OUTSIDE_RADIUS"
    assert body["allowed_radius_meters"] == SESSION_RADIUS
    assert body["distance_meters"] > SESSION_RADIUS


async def test_submit_location_rejects_poor_accuracy(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_verification(client, ctx["session_id"])

    response = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 200},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is False
    assert body["code"] == "LOCATION_ACCURACY_TOO_LOW"


async def test_submit_location_rejects_wrong_student(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_verification(client, ctx["session_id"])

    await create_student(
        db_session,
        ctx["branch"],
        ctx["division"],
        ctx["academic_year"],
        email="test-student-other@example.com",
        prn="STU-9002",
    )
    await db_session.commit()
    await login(client, "test-student-other@example.com", "password123")

    response = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_INVALID"


async def test_submit_location_not_found(client: AsyncClient, db_session: AsyncSession) -> None:
    _, academic_year, branch, division = await create_academic_context(db_session)
    await create_student(db_session, branch, division, academic_year)
    await db_session.commit()
    await login(client, "test-student@example.com", "password123")

    response = await client.post(
        "/api/v1/attendance/verifications/00000000-0000-0000-0000-000000000000/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_INVALID"


async def test_submit_location_rejects_expired_context(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_verification(client, ctx["session_id"])

    result = await db_session.execute(
        select(AttendanceVerification).where(AttendanceVerification.id == verification_id)
    )
    verification = result.scalar_one()
    verification.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERIFICATION_EXPIRED"


async def test_submit_location_rejects_wrong_step_state(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_verification(client, ctx["session_id"])

    result = await db_session.execute(
        select(AttendanceVerification).where(AttendanceVerification.id == verification_id)
    )
    verification = result.scalar_one()
    verification.status = VerificationStatus.FACE_VERIFIED
    await db_session.flush()

    response = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERIFICATION_STEP_INVALID"


async def test_submit_location_resubmission_overwrites_previous_attempt(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_verification(client, ctx["session_id"])

    first = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": FAR_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )
    assert first.json()["verified"] is False

    second = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )

    assert second.status_code == 200
    assert second.json()["verified"] is True


async def test_submit_location_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/attendance/verifications/00000000-0000-0000-0000-000000000000/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )
    assert response.status_code == 401
