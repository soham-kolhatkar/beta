"""Integration tests for /students/me and /faculty/me — real routing, real
Postgres via the transactional-rollback fixture. See test_auth.py's
docstring for why this tier vs. a unit test.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserRole
from tests.factories import (
    create_academic_context,
    create_faculty,
    create_student,
    create_user,
    login,
)


async def test_students_me_returns_seeded_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, academic_year, branch, division = await create_academic_context(db_session)
    await create_student(db_session, branch, division, academic_year)
    await db_session.commit()

    await login(client, "test-student@example.com", "password123")
    response = await client.get("/api/v1/students/me")

    assert response.status_code == 200
    body = response.json()
    assert body["prn"] == "STU-9001"
    assert body["user"]["email"] == "test-student@example.com"
    assert body["branch"]["code"] == "CS"
    assert body["division"]["name"] == "A"
    assert body["academic_year"]["name"] == "2026-27"
    assert body["face_registered"] is False


async def test_faculty_me_returns_seeded_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await create_faculty(db_session)
    await db_session.commit()

    await login(client, "test-faculty@example.com", "password123")
    response = await client.get("/api/v1/faculty/me")

    assert response.status_code == 200
    body = response.json()
    assert body["employee_id"] == "EMP-9001"
    assert body["user"]["email"] == "test-faculty@example.com"


async def test_students_me_404_for_user_without_student_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "test-admin@example.com", "password123", UserRole.ADMIN)
    await db_session.commit()

    await login(client, "test-admin@example.com", "password123")
    response = await client.get("/api/v1/students/me")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


async def test_students_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/students/me")
    assert response.status_code == 401
