"""Shared test data builders. Not pytest fixtures (they take parameters
per-call) — plain async helpers used across integration test modules.

Test emails must never collide with scripts/seed.py's fixture data,
since tests share the dev database rather than a separate test database
(a deliberate simplification, not an oversight — see PROGRESS.md). Use a
`test-` prefix, as this module's defaults do.
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


async def login(client: AsyncClient, email: str, password: str) -> None:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


async def create_academic_context(
    db_session: AsyncSession,
) -> tuple[Institution, AcademicYear, Branch, Division]:
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


async def create_user(db_session: AsyncSession, email: str, password: str, role: UserRole) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        name=f"Test {role.value.title()}",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def create_student(
    db_session: AsyncSession,
    branch: Branch,
    division: Division,
    academic_year: AcademicYear,
    email: str = "test-student@example.com",
    password: str = "password123",
    prn: str = "STU-9001",
) -> tuple[User, Student]:
    user = await create_user(db_session, email, password, UserRole.STUDENT)
    student = Student(
        user_id=user.id,
        prn=prn,
        roll_number="9",
        branch_id=branch.id,
        division_id=division.id,
        academic_year_id=academic_year.id,
    )
    db_session.add(student)
    await db_session.flush()
    return user, student


async def create_faculty(
    db_session: AsyncSession,
    email: str = "test-faculty@example.com",
    password: str = "password123",
    employee_id: str = "EMP-9001",
) -> tuple[User, Faculty]:
    user = await create_user(db_session, email, password, UserRole.FACULTY)
    faculty = Faculty(user_id=user.id, employee_id=employee_id, department="Computer Science")
    db_session.add(faculty)
    await db_session.flush()
    return user, faculty
