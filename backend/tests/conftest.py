"""Pytest configuration and fixtures for AgentShield tests."""
import os
import sys

import pytest

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Default for unit tests (no DB) - integration tests override via fixture
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://agentshield:agentshield@localhost:5432/agentshield",
)


def _get_asyncpg_url(url: str) -> str:
    """Convert postgres URL to asyncpg format."""
    if "asyncpg" in url:
        return url
    if "postgresql://" in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "postgres://" in url:
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url.replace("psycopg2", "asyncpg", 1) if "psycopg2" in url else url


@pytest.fixture(scope="session")
def postgres_url():
    """Start Postgres container and yield connection URL. Requires Docker.
    Set env INTEGRATION_USE_LOCAL_DB=1 to skip testcontainers and use local Postgres.
    """
    if os.environ.get("INTEGRATION_USE_LOCAL_DB") == "1":
        url = os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://agentshield:agentshield@localhost:5432/agentshield",
        )
        yield url
        return

    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip(
            "testcontainers not installed (pip install 'testcontainers[postgres]') "
            "or set INTEGRATION_USE_LOCAL_DB=1 with local Postgres"
        )

    with PostgresContainer("postgres:16-alpine") as postgres:
        url = postgres.get_connection_url()
        async_url = _get_asyncpg_url(url)
        if "postgresql://" in async_url and "+" not in async_url:
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        yield async_url


@pytest.fixture(scope="session")
def test_db_url(postgres_url):
    """Set DATABASE_URL for the test session. Must run before any app imports."""
    os.environ["DATABASE_URL"] = postgres_url
    yield postgres_url


@pytest.fixture
async def app_client(test_db_url):
    """
    Async HTTP client against the real FastAPI app with test database.
    Bootstraps tenant + API key before yielding.
    """
    from sqlalchemy import select

    from httpx import ASGITransport, AsyncClient

    # Import app ONLY after DATABASE_URL is set
    from app.core.config import settings
    from app.core.security import generate_api_key, hash_api_key
    from app.db.init_db import init_db
    from app.db.models import ApiKey, Policy, Tenant
    from app.db.session import async_session
    from app.main import app

    from scripts.bootstrap import STARTER_POLICY

    await init_db()

    async with async_session() as session:
        result = await session.execute(
            select(Tenant).where(Tenant.name == "test-tenant")
        )
        t = result.scalar_one_or_none()
        if not t:
            t = Tenant(name="test-tenant")
            session.add(t)
            await session.commit()
            await session.refresh(t)

        raw_key = generate_api_key(settings.API_KEY_PREFIX)
        ak = ApiKey(
            tenant_id=t.id,
            name="test-admin",
            key_hash=hash_api_key(raw_key),
            scopes=["admin"],
            is_active=True,
        )
        session.add(ak)

        result = await session.execute(
            select(Policy).where(
                Policy.tenant_id == t.id,
                Policy.name == "starter",
            )
        )
        if result.scalar_one_or_none() is None:
            p = Policy(
                tenant_id=t.id,
                name="starter",
                enabled=True,
                dsl=STARTER_POLICY,
                version=1,
            )
            session.add(p)

        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Api-Key": raw_key, "Content-Type": "application/json"},
    ) as client:
        yield client, raw_key
