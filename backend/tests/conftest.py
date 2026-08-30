from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import engine, get_db
from app.core.rate_limit import (
    face_processing_rate_limiter,
    login_rate_limiter,
    verification_rate_limiter,
)
from app.main import app


# The app's lifespan (where FastAPILimiter.init() would normally run) never
# fires under ASGITransport, so these dependencies would otherwise raise
# "You must call FastAPILimiter.init..." on first use. Overridden to no-ops
# here rather than initializing a real limiter, since the suite's own
# `login()` helper alone is called far more than any real rate limit allows
# across a full run. tests/test_rate_limiting.py is the one place that
# exercises the real Redis-backed limiter, via its own dedicated fixture.
async def _no_rate_limit() -> None:
    return None


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Wraps each test in a transaction that is rolled back afterward, so
    tests never leave data behind or depend on each other (docs/PLAN.md
    Phase 0: "test framework + DB fixture strategy decided now").
    """
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[login_rate_limiter] = _no_rate_limit
    app.dependency_overrides[face_processing_rate_limiter] = _no_rate_limit
    app.dependency_overrides[verification_rate_limiter] = _no_rate_limit

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
