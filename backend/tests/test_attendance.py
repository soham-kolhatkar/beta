"""Integration tests for attendance sessions (Phase 4, faculty side):
POST/GET /attendance/sessions, POST /attendance/sessions/{id}/end,
GET /attendance/sessions/active, GET /faculty/me/{classes,sessions}. Real
routing, real Postgres via the transactional-rollback fixture — see
test_auth.py's docstring for why this tier vs. a unit test.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import (
    create_academic_context,
    create_class_offering,
    create_enrollment,
    create_faculty,
    create_student,
    login,
)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


async def _setup(db_session: AsyncSession) -> dict[str, Any]:
    """One faculty owning one class, with one enrolled student."""
    institution, academic_year, branch, division = await create_academic_context(db_session)
    _, faculty = await create_faculty(db_session)
    _, student = await create_student(db_session, branch, division, academic_year)
    class_offering = await create_class_offering(
        db_session, institution, faculty, division, academic_year
    )
    await create_enrollment(db_session, class_offering, student)
    await db_session.commit()

    return {
        "institution": institution,
        "academic_year": academic_year,
        "branch": branch,
        "division": division,
        "faculty": faculty,
        "student": student,
        "class_id": str(class_offering.id),
    }


def _session_payload(class_id: str, **overrides: Any) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    payload = {
        "class_id": class_id,
        "starts_at": _iso(now),
        "ends_at": _iso(now + timedelta(hours=1)),
        "latitude": 18.5204,
        "longitude": 73.8567,
        "radius_meters": 100,
    }
    payload.update(overrides)
    return payload


async def test_create_session_success(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")

    response = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )

    assert response.status_code == 201
    body = response.json()
    assert body["class_id"] == ctx["class_id"]
    assert body["status"] == "ACTIVE"


async def test_create_session_rejects_unowned_class(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await create_faculty(db_session, email="test-faculty2@example.com", employee_id="EMP-9002")
    await db_session.commit()
    await login(client, "test-faculty2@example.com", "password123")

    response = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_create_session_requires_faculty_role(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-student@example.com", "password123")

    response = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_create_session_rejects_invalid_time_range(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    now = datetime.now(timezone.utc)

    response = await client.post(
        "/api/v1/attendance/sessions",
        json=_session_payload(
            ctx["class_id"], starts_at=_iso(now), ends_at=_iso(now - timedelta(minutes=5))
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


async def test_create_session_rejects_time_range_already_over(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    now = datetime.now(timezone.utc)

    response = await client.post(
        "/api/v1/attendance/sessions",
        json=_session_payload(
            ctx["class_id"],
            starts_at=_iso(now - timedelta(hours=2)),
            ends_at=_iso(now - timedelta(hours=1)),
        ),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


async def test_create_session_rejects_radius_out_of_bounds(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")

    response = await client.post(
        "/api/v1/attendance/sessions",
        json=_session_payload(ctx["class_id"], radius_meters=5),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


async def test_create_session_rejects_overlapping_conflict(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")

    first = await client.post("/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"]))
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "SESSION_CONFLICT"


async def test_create_session_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/attendance/sessions",
        json=_session_payload("00000000-0000-0000-0000-000000000000"),
    )
    assert response.status_code == 401


async def test_end_session_success(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )
    session_id = created.json()["id"]

    response = await client.post(f"/api/v1/attendance/sessions/{session_id}/end")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ENDED"
    assert body["ended_at"] is not None


async def test_end_session_rejects_other_faculty(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )
    session_id = created.json()["id"]

    await create_faculty(db_session, email="test-faculty3@example.com", employee_id="EMP-9003")
    await db_session.commit()
    await login(client, "test-faculty3@example.com", "password123")

    response = await client.post(f"/api/v1/attendance/sessions/{session_id}/end")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_end_session_not_found(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_faculty(db_session)
    await db_session.commit()
    await login(client, "test-faculty@example.com", "password123")

    response = await client.post(
        "/api/v1/attendance/sessions/00000000-0000-0000-0000-000000000000/end"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"


async def test_end_session_is_idempotent(client: AsyncClient, db_session: AsyncSession) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )
    session_id = created.json()["id"]

    first = await client.post(f"/api/v1/attendance/sessions/{session_id}/end")
    second = await client.post(f"/api/v1/attendance/sessions/{session_id}/end")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "ENDED"


async def test_get_session_detail_for_owning_faculty(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )
    session_id = created.json()["id"]

    response = await client.get(f"/api/v1/attendance/sessions/{session_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["class"]["id"] == ctx["class_id"]
    assert body["subject"]["code"] == "TST"
    assert body["faculty"]["name"] == "Test Faculty"
    assert body["status"] == "ACTIVE"


async def test_get_session_detail_rejects_other_faculty(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )
    session_id = created.json()["id"]

    await create_faculty(db_session, email="test-faculty4@example.com", employee_id="EMP-9004")
    await db_session.commit()
    await login(client, "test-faculty4@example.com", "password123")

    response = await client.get(f"/api/v1/attendance/sessions/{session_id}")

    assert response.status_code == 403


async def test_get_session_detail_for_enrolled_student(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )
    session_id = created.json()["id"]

    await login(client, "test-student@example.com", "password123")
    response = await client.get(f"/api/v1/attendance/sessions/{session_id}")

    assert response.status_code == 200


async def test_get_session_detail_rejects_unenrolled_student(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )
    session_id = created.json()["id"]

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

    response = await client.get(f"/api/v1/attendance/sessions/{session_id}")

    assert response.status_code == 403


async def test_get_session_detail_not_found(client: AsyncClient, db_session: AsyncSession) -> None:
    await create_faculty(db_session)
    await db_session.commit()
    await login(client, "test-faculty@example.com", "password123")

    response = await client.get("/api/v1/attendance/sessions/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"


async def test_list_active_sessions_includes_eligible_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    await client.post("/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"]))

    await login(client, "test-student@example.com", "password123")
    response = await client.get("/api/v1/attendance/sessions/active")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["class"]["id"] == ctx["class_id"]
    assert items[0]["faculty"] == {"name": "Test Faculty"}


async def test_list_active_sessions_excludes_unenrolled_student(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    await client.post("/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"]))

    await create_student(
        db_session,
        ctx["branch"],
        ctx["division"],
        ctx["academic_year"],
        email="test-student-other2@example.com",
        prn="STU-9003",
    )
    await db_session.commit()
    await login(client, "test-student-other2@example.com", "password123")

    response = await client.get("/api/v1/attendance/sessions/active")

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_list_active_sessions_excludes_future_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    now = datetime.now(timezone.utc)
    await client.post(
        "/api/v1/attendance/sessions",
        json=_session_payload(
            ctx["class_id"],
            starts_at=_iso(now + timedelta(hours=2)),
            ends_at=_iso(now + timedelta(hours=3)),
        ),
    )

    await login(client, "test-student@example.com", "password123")
    response = await client.get("/api/v1/attendance/sessions/active")

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_faculty_classes_lists_owned_classes_with_student_count(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")

    response = await client.get("/api/v1/faculty/me/classes")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == ctx["class_id"]
    assert items[0]["subject"]["code"] == "TST"
    assert items[0]["student_count"] == 1


async def test_faculty_sessions_filters_by_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    ctx = await _setup(db_session)
    await login(client, "test-faculty@example.com", "password123")
    created = await client.post(
        "/api/v1/attendance/sessions", json=_session_payload(ctx["class_id"])
    )
    session_id = created.json()["id"]
    await client.post(f"/api/v1/attendance/sessions/{session_id}/end")

    active_response = await client.get("/api/v1/faculty/me/sessions?status=ACTIVE")
    ended_response = await client.get("/api/v1/faculty/me/sessions?status=ENDED")

    assert active_response.json()["items"] == []
    assert len(ended_response.json()["items"]) == 1
    assert ended_response.json()["items"][0]["id"] == session_id
