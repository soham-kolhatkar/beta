"""Integration tests for the face + complete steps (Phase 5b):
POST /attendance/verifications/{id}/face, POST
/attendance/verifications/{id}/complete. Real routing, real Postgres via
the transactional-rollback fixture — see test_auth.py's docstring for why
this tier vs. a unit test. Sessions/verification-through-location are
built via the real Phase 4/5a endpoints, not inserted directly.
"""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import face_model
from app.models.attendance import Attendance
from app.models.attendance_verification import AttendanceVerification
from app.repositories import attendance_repository
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


def _blank_image_bytes() -> bytes:
    import io

    image = Image.fromarray(np.full((300, 300, 3), 200, dtype=np.uint8))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


def _real_face_embedding() -> list[float]:
    image = face_service.decode_image("image/jpeg", FIXTURE_FACE)
    return face_model.extract_embedding(image)


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
    client: AsyncClient, db_session: AsyncSession, *, matching_face: bool = True
) -> dict[str, Any]:
    """Faculty owning one class, one enrolled student registered with
    either the fixture's real embedding (`matching_face=True`, so a live
    submission of the same photo matches) or a deliberately different one
    (so it doesn't), plus a currently-active session for that class.
    """
    institution, academic_year, branch, division = await create_academic_context(db_session)
    _, faculty = await create_faculty(db_session)
    _, student = await create_student(db_session, branch, division, academic_year)
    class_offering = await create_class_offering(
        db_session, institution, faculty, division, academic_year
    )
    await create_enrollment(db_session, class_offering, student)

    if matching_face:
        embedding = _real_face_embedding()
    else:
        # Effectively orthogonal to any real face embedding -> cosine
        # distance ~1.0, well past the 0.30 threshold.
        embedding = np.random.default_rng(42).standard_normal(512).tolist()
    await create_face_profile(db_session, student, embedding=embedding)
    await db_session.commit()

    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(str(class_offering.id))
    )
    assert created.status_code == 201

    return {
        "branch": branch,
        "division": division,
        "academic_year": academic_year,
        "class_id": str(class_offering.id),
        "session_id": created.json()["id"],
        "student": student,
    }


async def _start_and_verify_location(client: AsyncClient, session_id: str) -> str:
    await login(client, "test-student@example.com", "password123")
    start = await client.post(f"/api/v1/attendance/sessions/{session_id}/verification")
    assert start.status_code == 200
    verification_id = start.json()["verification_id"]

    location = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/location",
        json={"latitude": SESSION_LAT, "longitude": SESSION_LON, "accuracy_meters": 10},
    )
    assert location.status_code == 200
    assert location.json()["verified"] is True
    return verification_id


async def _verify_face(client: AsyncClient, verification_id: str) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/face",
        files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")},
    )
    return response


async def _get_verification(
    db_session: AsyncSession, verification_id: str
) -> AttendanceVerification:
    result = await db_session.execute(
        select(AttendanceVerification).where(AttendanceVerification.id == verification_id)
    )
    return result.scalar_one()


async def test_submit_face_success(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])

    response = await _verify_face(client, verification_id)

    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is True
    assert body["next_step"] == "COMPLETE"


async def test_submit_face_rejects_mismatch(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup(client, db_session, matching_face=False)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])

    response = await _verify_face(client, verification_id)

    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is False
    assert body["code"] == "FACE_NOT_VERIFIED"
    assert body["retryable"] is True


async def test_submit_face_rejects_no_face_detected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])

    response = await client.post(
        f"/api/v1/attendance/verifications/{verification_id}/face",
        files={"image": ("blank.jpg", _blank_image_bytes(), "image/jpeg")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FACE_NOT_DETECTED"


async def test_submit_face_rejects_before_location(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await login(client, "test-student@example.com", "password123")
    start = await client.post(f"/api/v1/attendance/sessions/{ctx['session_id']}/verification")
    verification_id = start.json()["verification_id"]

    response = await _verify_face(client, verification_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERIFICATION_STEP_INVALID"


async def test_submit_face_rejects_wrong_student(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])

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

    response = await _verify_face(client, verification_id)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_INVALID"


async def test_submit_face_not_found(client: AsyncClient, db_session: AsyncSession) -> None:
    _, academic_year, branch, division = await create_academic_context(db_session)
    await create_student(db_session, branch, division, academic_year)
    await db_session.commit()
    await login(client, "test-student@example.com", "password123")

    response = await client.post(
        "/api/v1/attendance/verifications/00000000-0000-0000-0000-000000000000/face",
        files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_INVALID"


async def test_submit_face_rejects_expired_context(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])

    verification = await _get_verification(db_session, verification_id)
    verification.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()

    response = await _verify_face(client, verification_id)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERIFICATION_EXPIRED"


async def test_submit_face_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/attendance/verifications/00000000-0000-0000-0000-000000000000/face",
        files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")},
    )
    assert response.status_code == 401


async def test_complete_success(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])
    face_response = await _verify_face(client, verification_id)
    assert face_response.json()["verified"] is True

    response = await client.post(f"/api/v1/attendance/verifications/{verification_id}/complete")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PRESENT"
    assert "attendance_id" in body
    assert "marked_at" in body

    result = await db_session.execute(
        select(Attendance).where(Attendance.id == uuid.UUID(body["attendance_id"]))
    )
    attendance = result.scalar_one()
    assert attendance.student_id == ctx["student"].id
    assert attendance.face_verified is True
    assert attendance.face_score is not None
    assert attendance.distance_meters < 1


async def test_complete_rejects_before_face_verified(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])

    response = await client.post(f"/api/v1/attendance/verifications/{verification_id}/complete")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERIFICATION_STEP_INVALID"


async def test_complete_rejects_wrong_student(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])
    await _verify_face(client, verification_id)

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

    response = await client.post(f"/api/v1/attendance/verifications/{verification_id}/complete")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_INVALID"


async def test_complete_rejects_expired_context(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])
    await _verify_face(client, verification_id)

    verification = await _get_verification(db_session, verification_id)
    verification.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.flush()

    response = await client.post(f"/api/v1/attendance/verifications/{verification_id}/complete")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERIFICATION_EXPIRED"


async def test_complete_rejects_ended_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])
    await _verify_face(client, verification_id)

    await login(client, "test-faculty@example.com", "password123")
    end_response = await client.post(f"/api/v1/attendance/sessions/{ctx['session_id']}/end")
    assert end_response.status_code == 200

    await login(client, "test-student@example.com", "password123")
    response = await client.post(f"/api/v1/attendance/verifications/{verification_id}/complete")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"


async def test_complete_rejects_duplicate_marking(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)

    first_verification_id = await _start_and_verify_location(client, ctx["session_id"])
    await _verify_face(client, first_verification_id)
    first = await client.post(f"/api/v1/attendance/verifications/{first_verification_id}/complete")
    assert first.status_code == 200

    second_verification_id = await _start_and_verify_location(client, ctx["session_id"])
    await _verify_face(client, second_verification_id)
    second = await client.post(
        f"/api/v1/attendance/verifications/{second_verification_id}/complete"
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ATTENDANCE_ALREADY_MARKED"


async def test_complete_database_constraint_rejects_duplicate_insert(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Proves the DB-level UNIQUE(session_id, student_id) constraint
    itself — not just the service's own pre-check — is what actually
    prevents duplicate attendance (docs/ARCHITECTURE.md §25, "the single
    most important constraint in the system"). The transactional-rollback
    fixture shares one connection/transaction across a test, so it can't
    simulate two genuinely-concurrent connections racing the same insert;
    this instead calls the repository directly a second time for the same
    key, bypassing the service's pre-check, to confirm the constraint
    underneath it holds regardless.
    """
    ctx = await _setup(client, db_session)
    verification_id = await _start_and_verify_location(client, ctx["session_id"])
    await _verify_face(client, verification_id)
    first = await client.post(f"/api/v1/attendance/verifications/{verification_id}/complete")
    assert first.status_code == 200

    with pytest.raises(IntegrityError):
        await attendance_repository.create(
            db_session,
            session_id=uuid.UUID(ctx["session_id"]),
            student_id=ctx["student"].id,
            marked_at=datetime.now(timezone.utc),
            latitude=SESSION_LAT,
            longitude=SESSION_LON,
            location_accuracy=10.0,
            distance_meters=0.0,
            face_verified=True,
            face_score=0.1,
        )
    # The failed flush above leaves Postgres's side of the transaction
    # aborted; the fixture's own teardown (conftest.py's `db_session`)
    # still cleans up correctly, but emits a harmless
    # "transaction already deassociated from connection" SAWarning when it
    # does — an artifact of deliberately triggering a real constraint
    # violation inside a fixture built around one long-lived transaction,
    # not a sign anything is actually wrong here.


async def test_complete_not_found(client: AsyncClient, db_session: AsyncSession) -> None:
    _, academic_year, branch, division = await create_academic_context(db_session)
    await create_student(db_session, branch, division, academic_year)
    await db_session.commit()
    await login(client, "test-student@example.com", "password123")

    response = await client.post(
        "/api/v1/attendance/verifications/00000000-0000-0000-0000-000000000000/complete"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VERIFICATION_INVALID"


async def test_complete_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/attendance/verifications/00000000-0000-0000-0000-000000000000/complete"
    )
    assert response.status_code == 401
