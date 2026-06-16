import os

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer

from app.core import db as db_module
from app.main import app
from app.models.base import Base


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    with PostgresContainer("pgvector/pgvector:pg16") as pc:
        yield pc


@pytest.fixture(scope="session")
def postgres_async_url(postgres_container: PostgresContainer) -> str:
    return postgres_container.get_connection_url(driver="asyncpg")


@pytest.fixture
async def async_engine(postgres_async_url: str) -> AsyncEngine:
    engine = create_async_engine(postgres_async_url, pool_size=2, max_overflow=2)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, Any]:
    session_local = async_sessionmaker(
        bind=async_engine, expire_on_commit=False, autoflush=False
    )
    async with session_local() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture
async def client(
    async_engine: AsyncEngine, db_session: AsyncSession
) -> AsyncGenerator[AsyncClient, Any]:
    async def override_get_session() -> AsyncGenerator[AsyncSession, Any]:
        yield db_session

    app.dependency_overrides[db_module.get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with LifespanManager(app):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
