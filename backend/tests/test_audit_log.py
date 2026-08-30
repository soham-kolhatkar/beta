"""Integration tests for Phase 7's audit log (docs/DATABASE.md §33):
session creation/end and face registration each write an `AuditLog` row.
There's no read API for these yet (no admin UI — same deliberate scope
limit as every other phase, per docs/UI.md §63), so assertions query the
table directly via the ORM, same precedent as the DB-constraint test in
test_attendance_completion.py.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import face_model
from app.models.audit_log import AuditLog
from app.services import face_service
from tests.factories import (
    create_academic_context,
    create_class_offering,
    create_enrollment,
    create_faculty,
    create_student,
    login,
)

FIXTURE_FACE = (Path(__file__).parent / "fixtures" / "face.jpg").read_bytes()

SESSION_LAT = 18.5204
SESSION_LON = 73.8567
SESSION_RADIUS = 100


async def _logs_for(db_session: AsyncSession, entity_id, action: str) -> list[AuditLog]:
    result = await db_session.execute(
        select(AuditLog).where(AuditLog.entity_id == entity_id, AuditLog.action == action)
    )
    return list(result.scalars().all())


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


async def test_session_creation_writes_audit_log(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await login(client, "test-faculty@example.com", "password123")

    now = datetime.now(timezone.utc)
    response = await client.post(
        "/api/v1/attendance/sessions",
        json={
            "class_id": ctx["class_id"],
            "starts_at": (now - timedelta(minutes=5)).isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
            "latitude": SESSION_LAT,
            "longitude": SESSION_LON,
            "radius_meters": SESSION_RADIUS,
        },
    )
    assert response.status_code == 201
    session_id = response.json()["id"]

    logs = await _logs_for(db_session, session_id, "SESSION_CREATED")
    assert len(logs) == 1
    assert logs[0].user_id == ctx["faculty"].user_id
    assert logs[0].entity_type == "attendance_session"
    assert logs[0].details == {"class_id": ctx["class_id"]}


async def test_session_end_writes_audit_log_once(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await login(client, "test-faculty@example.com", "password123")

    now = datetime.now(timezone.utc)
    created = await client.post(
        "/api/v1/attendance/sessions",
        json={
            "class_id": ctx["class_id"],
            "starts_at": (now - timedelta(minutes=5)).isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
            "latitude": SESSION_LAT,
            "longitude": SESSION_LON,
            "radius_meters": SESSION_RADIUS,
        },
    )
    session_id = created.json()["id"]

    first_end = await client.post(f"/api/v1/attendance/sessions/{session_id}/end")
    assert first_end.status_code == 200
    second_end = await client.post(f"/api/v1/attendance/sessions/{session_id}/end")
    assert second_end.status_code == 200

    # The second call is a no-op (idempotent end) — must not double-log.
    logs = await _logs_for(db_session, session_id, "SESSION_ENDED")
    assert len(logs) == 1


async def test_face_registration_writes_audit_log(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, db_session)
    await login(client, "test-student@example.com", "password123")

    response = await client.post(
        "/api/v1/students/me/face",
        files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")},
    )
    assert response.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "FACE_PROFILE_REGISTERED",
            AuditLog.user_id == ctx["student"].user_id,
        )
    )
    logs = list(result.scalars().all())
    assert len(logs) == 1
    assert logs[0].entity_type == "face_profile"


async def test_face_reregistration_writes_a_second_audit_log(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Re-registration replaces the FaceProfile row (upsert, Phase 3) but
    should still be its own auditable event each time.
    """
    ctx = await _setup(client, db_session)
    image = face_service.decode_image("image/jpeg", FIXTURE_FACE)
    face_model.extract_embedding(image)  # warms the model before timing-sensitive calls below
    await login(client, "test-student@example.com", "password123")

    first = await client.post(
        "/api/v1/students/me/face", files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")}
    )
    second = await client.post(
        "/api/v1/students/me/face", files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")}
    )
    assert first.status_code == second.status_code == 200

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.action == "FACE_PROFILE_REGISTERED",
            AuditLog.user_id == ctx["student"].user_id,
        )
    )
    assert len(list(result.scalars().all())) == 2
