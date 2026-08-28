from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import engine, get_db
from app.main import app


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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
