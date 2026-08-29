"""Integration tests for /students/me/face. Uses a real face photo fixture
(tests/fixtures/face.jpg) so the actual DeepFace pipeline runs end-to-end,
not a mocked version of it — face detection/embedding correctness is
exactly what would go silently wrong if mocked.
"""

from pathlib import Path

import numpy as np
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face_profile import FaceProfile
from app.models.student import Student
from app.models.user import UserRole
from tests.factories import create_academic_context, create_student, create_user, login

FIXTURE_FACE = (Path(__file__).parent / "fixtures" / "face.jpg").read_bytes()


def _blank_image_bytes() -> bytes:
    import io

    image = Image.fromarray(np.full((300, 300, 3), 200, dtype=np.uint8))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()


async def _login_as_student(client: AsyncClient, db_session: AsyncSession) -> Student:
    _, academic_year, branch, division = await create_academic_context(db_session)
    _, student = await create_student(db_session, branch, division, academic_year)
    await db_session.commit()
    await login(client, "test-student@example.com", "password123")
    return student


async def test_register_face_success(client: AsyncClient, db_session: AsyncSession) -> None:
    await _login_as_student(client, db_session)

    response = await client.post(
        "/api/v1/students/me/face",
        files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["face_registered"] is True
    assert body["model"]["name"] == "Facenet512"

    status_response = await client.get("/api/v1/students/me/face")
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["registered"] is True
    assert status_body["model"]["name"] == "Facenet512"


async def test_register_face_replaces_existing_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await _login_as_student(client, db_session)

    for _ in range(2):
        response = await client.post(
            "/api/v1/students/me/face",
            files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")},
        )
        assert response.status_code == 200

    # Scoped to this test's own student: the dev database is shared (not a
    # separate test DB — see tests/factories.py), so other students' rows
    # (from scripts/seed.py or manual testing) may legitimately coexist here.
    result = await db_session.execute(
        select(FaceProfile).where(FaceProfile.student_id == student.id)
    )
    profiles = result.scalars().all()
    assert len(profiles) == 1


async def test_register_face_rejects_no_face_detected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _login_as_student(client, db_session)

    response = await client.post(
        "/api/v1/students/me/face",
        files={"image": ("blank.jpg", _blank_image_bytes(), "image/jpeg")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FACE_NOT_DETECTED"


async def test_register_face_rejects_unsupported_content_type(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _login_as_student(client, db_session)

    response = await client.post(
        "/api/v1/students/me/face",
        files={"image": ("not-an-image.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


async def test_register_face_requires_student_profile(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "test-faculty2@example.com", "password123", UserRole.FACULTY)
    await db_session.commit()
    await login(client, "test-faculty2@example.com", "password123")

    response = await client.post(
        "/api/v1/students/me/face",
        files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


async def test_register_face_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/students/me/face",
        files={"image": ("face.jpg", FIXTURE_FACE, "image/jpeg")},
    )
    assert response.status_code == 401


async def test_face_status_not_registered_by_default(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _login_as_student(client, db_session)

    response = await client.get("/api/v1/students/me/face")

    assert response.status_code == 200
    body = response.json()
    assert body["registered"] is False
    assert body["model"] is None
