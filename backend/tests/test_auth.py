"""Integration tests: real routing, real cookie handling, real Postgres
(via the transactional-rollback fixture) — nothing mocked. See
docs/ARCHITECTURE.md §32 "Backend integration tests: API + database,
Authentication flow." Pure-logic unit tests for the hashing primitives
live in test_security.py.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole


async def _create_user(
    db_session: AsyncSession, email: str = "test-student@example.com", password: str = "password123"
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        name="Test Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def test_login_success(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_user(db_session)

    response = await client.post(
        "/api/v1/auth/login", json={"email": "test-student@example.com", "password": "password123"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test-student@example.com"
    assert body["role"] == "STUDENT"
    assert response.cookies

    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "test-student@example.com"


async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_user(db_session)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test-student@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_unknown_email_matches_wrong_password_response(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _create_user(db_session)

    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"email": "test-student@example.com", "password": "wrong-password"},
    )
    unknown_email = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_me_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


async def test_logout_invalidates_session(client: AsyncClient, db_session: AsyncSession) -> None:
    await _create_user(db_session)

    await client.post(
        "/api/v1/auth/login", json={"email": "test-student@example.com", "password": "password123"}
    )
    assert (await client.get("/api/v1/auth/me")).status_code == 200

    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_login_ignores_a_smuggled_role_field(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """docs/SECURITY.md §69 item 7 ("cannot escalate role"): no endpoint in
    this API accepts a `role` field as input anywhere (grepped every
    request schema to confirm) — `role` only ever appears in output. This
    is the structural mitigation; this test proves a client can't smuggle
    one into the one write endpoint whose response shape happens to include
    `role`, `/auth/login`, and have it do anything.
    """
    await _create_user(db_session)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test-student@example.com", "password": "password123", "role": "ADMIN"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "STUDENT"


async def test_inactive_user_cannot_login(client: AsyncClient, db_session: AsyncSession) -> None:
    user = await _create_user(db_session)
    user.is_active = False
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/login", json={"email": "test-student@example.com", "password": "password123"}
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
