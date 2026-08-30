"""Idempotent dev-only seed script.

Builds a coherent institution -> year -> branch -> division ->
students/faculty -> classes -> enrollments graph (docs/DATABASE.md
§9-19), on top of the Phase 1 seed users. This is the Phase 2-8
substitute for admin CRUD UI (docs/UI.md §63).

Usage: uv run python scripts/seed.py
"""

import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.academic_year import AcademicYear
from app.models.attendance import Attendance
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.branch import Branch
from app.models.class_enrollment import ClassEnrollment
from app.models.class_offering import ClassOffering
from app.models.division import Division
from app.models.faculty import Faculty
from app.models.institution import Institution
from app.models.student import Student
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.repositories import (
    academic_year_repository,
    branch_repository,
    class_enrollment_repository,
    class_offering_repository,
    division_repository,
    faculty_repository,
    institution_repository,
    student_repository,
    subject_repository,
    user_repository,
)

# A seeded session location (arbitrary campus coordinates) reused for every
# backdated session below — these rows are inserted directly, not through
# attendance_session_service, so nothing actually validates against them.
SEED_SESSION_LAT = 18.5204
SEED_SESSION_LON = 73.8567
SEED_SESSION_RADIUS = 100.0

# Fixed present/absent pattern (most-recent day first) so re-running the
# seed script is deterministic rather than depending on `random`. ~80%
# attendance, with one class's pattern reversed for a bit of variety.
ATTENDANCE_PATTERN = [True, True, False, True, True, True, False, True, True, True]

# Dev-only known passwords. Never use this pattern in production — real
# account creation belongs to an admin-driven process (docs/PRODUCT.md §4).
SEED_USERS = [
    {
        "email": "student@example.com",
        "password": "password123",
        "name": "Aarav Sharma",
        "role": UserRole.STUDENT,
    },
    {
        "email": "faculty@example.com",
        "password": "password123",
        "name": "Professor XYZ",
        "role": UserRole.FACULTY,
    },
    {
        "email": "admin@example.com",
        "password": "password123",
        "name": "Admin User",
        "role": UserRole.ADMIN,
    },
]


async def seed_users(db: AsyncSession) -> dict[str, User]:
    users_by_email = {}
    for entry in SEED_USERS:
        existing = await user_repository.get_by_email(db, entry["email"])
        password_hash = hash_password(entry["password"])

        if existing is None:
            user = User(
                email=entry["email"].strip().lower(),
                password_hash=password_hash,
                name=entry["name"],
                role=entry["role"],
                is_active=True,
            )
            db.add(user)
            print(f"created user {entry['email']} ({entry['role'].value})")
        else:
            user = existing
            user.password_hash = password_hash
            user.name = entry["name"]
            user.role = entry["role"]
            user.is_active = True
            print(f"updated user {entry['email']} ({entry['role'].value})")

        await db.flush()
        users_by_email[entry["email"]] = user

    return users_by_email


async def seed_academic_graph(db: AsyncSession, users_by_email: dict[str, User]) -> None:
    institution = await institution_repository.get_by_code(db, "EIT")
    if institution is None:
        institution = Institution(name="Example Institute of Technology", code="EIT")
        db.add(institution)
        await db.flush()
        print("created institution EIT")

    academic_year = await academic_year_repository.get_by_institution_and_name(
        db, institution.id, "2026-27"
    )
    if academic_year is None:
        academic_year = AcademicYear(
            institution_id=institution.id,
            name="2026-27",
            start_date=date(2026, 6, 1),
            end_date=date(2027, 5, 31),
            is_active=True,
        )
        db.add(academic_year)
        await db.flush()
        print("created academic year 2026-27")

    branch = await branch_repository.get_by_institution_and_code(db, institution.id, "CS")
    if branch is None:
        branch = Branch(institution_id=institution.id, name="Computer Science", code="CS")
        db.add(branch)
        await db.flush()
        print("created branch CS")

    division = await division_repository.get_by_branch_year_name(
        db, branch.id, academic_year.id, "A"
    )
    if division is None:
        division = Division(
            institution_id=institution.id,
            branch_id=branch.id,
            academic_year_id=academic_year.id,
            name="A",
        )
        db.add(division)
        await db.flush()
        print("created division CS-A")

    subject = await subject_repository.get_by_institution_and_code(db, institution.id, "DBMS")
    if subject is None:
        subject = Subject(
            institution_id=institution.id, name="Database Management Systems", code="DBMS"
        )
        db.add(subject)
        await db.flush()
        print("created subject DBMS")

    student_user = users_by_email["student@example.com"]
    student = await student_repository.get_by_prn(db, "STU-0001")
    if student is None:
        student = Student(
            user_id=student_user.id,
            prn="STU-0001",
            roll_number="1",
            branch_id=branch.id,
            division_id=division.id,
            academic_year_id=academic_year.id,
        )
        db.add(student)
        await db.flush()
        print("created student profile STU-0001")

    faculty_user = users_by_email["faculty@example.com"]
    faculty = await faculty_repository.get_by_employee_id(db, "EMP-0001")
    if faculty is None:
        faculty = Faculty(
            user_id=faculty_user.id, employee_id="EMP-0001", department="Computer Science"
        )
        db.add(faculty)
        await db.flush()
        print("created faculty profile EMP-0001")

    class_offering = await class_offering_repository.get_by_natural_key(
        db, subject.id, faculty.id, division.id, academic_year.id
    )
    if class_offering is None:
        class_offering = ClassOffering(
            institution_id=institution.id,
            subject_id=subject.id,
            faculty_id=faculty.id,
            division_id=division.id,
            academic_year_id=academic_year.id,
            name="DBMS - CS A",
        )
        db.add(class_offering)
        await db.flush()
        print("created class DBMS - CS A")

    enrollment = await class_enrollment_repository.get_by_class_and_student(
        db, class_offering.id, student.id
    )
    if enrollment is None:
        db.add(ClassEnrollment(class_id=class_offering.id, student_id=student.id))
        print("enrolled STU-0001 in DBMS - CS A")

    # Two more subjects/classes purely so the dashboards/history have more
    # than one row of real data to show. DBMS deliberately isn't given
    # backdated history here — it already has genuine accumulated history
    # from every prior phase's own manual HTTP testing (see PROGRESS.md),
    # and backfilling it would just mix synthetic rows into that.
    for subject_code, subject_name, class_name, pattern in [
        ("OS", "Operating Systems", "OS - CS A", ATTENDANCE_PATTERN),
        ("AI", "Artificial Intelligence", "AI - CS A", list(reversed(ATTENDANCE_PATTERN))),
    ]:
        subject = await subject_repository.get_by_institution_and_code(
            db, institution.id, subject_code
        )
        if subject is None:
            subject = Subject(institution_id=institution.id, name=subject_name, code=subject_code)
            db.add(subject)
            await db.flush()
            print(f"created subject {subject_code}")

        extra_class = await class_offering_repository.get_by_natural_key(
            db, subject.id, faculty.id, division.id, academic_year.id
        )
        if extra_class is None:
            extra_class = ClassOffering(
                institution_id=institution.id,
                subject_id=subject.id,
                faculty_id=faculty.id,
                division_id=division.id,
                academic_year_id=academic_year.id,
                name=class_name,
            )
            db.add(extra_class)
            await db.flush()
            print(f"created class {class_name}")

        extra_enrollment = await class_enrollment_repository.get_by_class_and_student(
            db, extra_class.id, student.id
        )
        if extra_enrollment is None:
            db.add(ClassEnrollment(class_id=extra_class.id, student_id=student.id))
            print(f"enrolled STU-0001 in {class_name}")

        await seed_attendance_history(db, extra_class, student, pattern)


async def seed_attendance_history(
    db: AsyncSession, class_offering: ClassOffering, student: Student, pattern: list[bool]
) -> None:
    """Backdated ended sessions + attendance rows for `class_offering`, one
    per day going backward from yesterday (so nothing shows up as "today"
    on the dashboard). Only runs if this class has zero sessions at all —
    idempotent in the same spirit as the rest of this script without
    needing a natural key per synthetic session.
    """
    existing = await db.execute(
        select(func.count())
        .select_from(AttendanceSession)
        .where(AttendanceSession.class_id == class_offering.id)
    )
    if existing.scalar_one() > 0:
        return

    now = datetime.now(timezone.utc)
    for day_offset, present in enumerate(pattern, start=1):
        starts_at = (now - timedelta(days=day_offset)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        ends_at = starts_at + timedelta(hours=1)

        session = AttendanceSession(
            class_id=class_offering.id,
            faculty_id=class_offering.faculty_id,
            latitude=SEED_SESSION_LAT,
            longitude=SEED_SESSION_LON,
            radius_meters=SEED_SESSION_RADIUS,
            starts_at=starts_at,
            ends_at=ends_at,
            status=SessionStatus.ENDED,
            ended_at=ends_at,
        )
        db.add(session)
        await db.flush()

        if present:
            db.add(
                Attendance(
                    session_id=session.id,
                    student_id=student.id,
                    marked_at=starts_at + timedelta(minutes=5),
                    latitude=SEED_SESSION_LAT,
                    longitude=SEED_SESSION_LON,
                    location_accuracy=10.0,
                    distance_meters=5.0,
                    face_verified=True,
                    face_score=0.15,
                )
            )
    print(f"backfilled {len(pattern)} sessions for {class_offering.name}")


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        users_by_email = await seed_users(db)
        await seed_academic_graph(db, users_by_email)
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
