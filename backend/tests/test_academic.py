"""Integration tests for /students/me and /faculty/me — real routing, real
Postgres via the transactional-rollback fixture. See test_auth.py's
docstring for why this tier vs. a unit test.
"""

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.academic_year import AcademicYear
from app.models.branch import Branch
from app.models.division import Division
from app.models.faculty import Faculty
from app.models.institution import Institution
from app.models.student import Student
from app.models.user import User, UserRole


async def _login(client: AsyncClient, email: str, password: str) -> None:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


async def _create_academic_context(db_session: AsyncSession):
    institution = Institution(name="Test Institute", code="TEST")
    db_session.add(institution)
    await db_session.flush()

    academic_year = AcademicYear(
        institution_id=institution.id,
        name="2026-27",
        start_date=date(2026, 6, 1),
        end_date=date(2027, 5, 31),
        is_active=True,
    )
    branch = Branch(institution_id=institution.id, name="Computer Science", code="CS")
    db_session.add_all([academic_year, branch])
    await db_session.flush()

    division = Division(
        institution_id=institution.id,
        branch_id=branch.id,
        academic_year_id=academic_year.id,
        name="A",
    )
    db_session.add(division)
    await db_session.flush()

    return institution, academic_year, branch, division


async def test_students_me_returns_seeded_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, academic_year, branch, division = await _create_academic_context(db_session)

    user = User(
        email="test-student@example.com",
        password_hash=hash_password("password123"),
        name="Test Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    student = Student(
        user_id=user.id,
        prn="STU-9001",
        roll_number="9",
        branch_id=branch.id,
        division_id=division.id,
        academic_year_id=academic_year.id,
    )
    db_session.add(student)
    await db_session.commit()

    await _login(client, "test-student@example.com", "password123")
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
    user = User(
        email="test-faculty@example.com",
        password_hash=hash_password("password123"),
        name="Test Faculty",
        role=UserRole.FACULTY,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    faculty = Faculty(user_id=user.id, employee_id="EMP-9001", department="Computer Science")
    db_session.add(faculty)
    await db_session.commit()

    await _login(client, "test-faculty@example.com", "password123")
    response = await client.get("/api/v1/faculty/me")

    assert response.status_code == 200
    body = response.json()
    assert body["employee_id"] == "EMP-9001"
    assert body["user"]["email"] == "test-faculty@example.com"


async def test_students_me_404_for_user_without_student_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user = User(
        email="test-admin@example.com",
        password_hash=hash_password("password123"),
        name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()

    await _login(client, "test-admin@example.com", "password123")
    response = await client.get("/api/v1/students/me")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


async def test_students_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/students/me")
    assert response.status_code == 401
