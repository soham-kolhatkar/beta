"""Integration tests for Phase 7's rate limiting: real Redis, real
routing — this is the one test module that doesn't use the shared `client`
fixture from conftest.py, because that fixture overrides the rate-limiter
dependencies to no-ops (the rest of the suite's `login()` helper alone is
called far more than any real limit allows across a full run).
`rate_limited_client` below sets up the real thing instead, against a
dedicated Redis logical DB (15) so it doesn't collide with counters from a
live dev server or another test run using the default DB.

docs/SECURITY.md §69 item 8: "Cannot bypass API rate limits."
"""

from collections.abc import AsyncGenerator

import pytest
import redis.asyncio as redis
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import redis as redis_module
from app.core.config import settings
from app.core.database import engine, get_db
from app.main import app
from app.models.user import UserRole
from tests.factories import create_user

TEST_REDIS_URL = "redis://localhost:6379/15"
TEST_PASSWORD = "password123"


@pytest.fixture
async def rate_limited_client() -> AsyncGenerator[AsyncClient, None]:
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()
    await create_user(session, "test-ratelimit@example.com", TEST_PASSWORD, UserRole.STUDENT)
    await session.commit()

    test_redis = redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await test_redis.flushdb()
    # Both the RateLimiter dependency and auth_service's per-email lockout
    # read the shared client via app.core.redis.get_client() — point it at
    # this freshly-flushed test Redis rather than whatever (if anything)
    # the real app lifespan set up.
    redis_module._client = test_redis

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        redis_module._client = None
        await test_redis.aclose()
        await session.close()
        await transaction.rollback()
        await connection.close()


async def test_login_ip_rate_limit_blocks_after_threshold(
    rate_limited_client: AsyncClient,
) -> None:
    # A different, nonexistent email per request keeps each email's own
    # lockout counter at 1 (never trips), isolating the IP-based limiter as
    # the mechanism under test here.
    for i in range(settings.login_rate_limit_times):
        response = await rate_limited_client.post(
            "/api/v1/auth/login",
            json={"email": f"test-flood-{i}@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    blocked = await rate_limited_client.post(
        "/api/v1/auth/login",
        json={"email": "test-flood-overflow@example.com", "password": "wrong"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


async def test_login_ip_rate_limit_not_bypassable_via_spoofed_forwarded_for(
    rate_limited_client: AsyncClient,
) -> None:
    for i in range(settings.login_rate_limit_times):
        await rate_limited_client.post(
            "/api/v1/auth/login",
            json={"email": f"test-flood2-{i}@example.com", "password": "wrong"},
        )

    # If the identifier trusted this header, a fresh spoofed IP would look
    # like a brand-new client with zero counted requests and get through.
    spoofed = await rate_limited_client.post(
        "/api/v1/auth/login",
        json={"email": "test-flood2-overflow@example.com", "password": "wrong"},
        headers={"X-Forwarded-For": "203.0.113.99"},
    )
    assert spoofed.status_code == 429


async def test_email_lockout_blocks_even_correct_password_after_threshold(
    rate_limited_client: AsyncClient,
) -> None:
    for _ in range(settings.auth_email_lockout_max_attempts):
        response = await rate_limited_client.post(
            "/api/v1/auth/login",
            json={"email": "test-ratelimit@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    # Well under the IP ceiling, so this is specifically the per-email
    # lockout firing — and it blocks the *correct* password too, proving
    # it's a real account lockout rather than coincidental 401s.
    locked_out = await rate_limited_client.post(
        "/api/v1/auth/login",
        json={"email": "test-ratelimit@example.com", "password": TEST_PASSWORD},
    )
    assert locked_out.status_code == 429
    assert locked_out.json()["error"]["code"] == "RATE_LIMITED"


async def test_successful_login_resets_the_failure_counter(
    rate_limited_client: AsyncClient,
) -> None:
    for _ in range(settings.auth_email_lockout_max_attempts - 1):
        response = await rate_limited_client.post(
            "/api/v1/auth/login",
            json={"email": "test-ratelimit@example.com", "password": "wrong"},
        )
        assert response.status_code == 401

    success = await rate_limited_client.post(
        "/api/v1/auth/login",
        json={"email": "test-ratelimit@example.com", "password": TEST_PASSWORD},
    )
    assert success.status_code == 200

    # If the counter hadn't reset, one more failure would tip it over the
    # threshold from where the previous block left off.
    after_reset = await rate_limited_client.post(
        "/api/v1/auth/login",
        json={"email": "test-ratelimit@example.com", "password": "wrong"},
    )
    assert after_reset.status_code == 401
