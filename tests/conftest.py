"""
Shared pytest fixtures for the Swaq test suite.
Uses an in-memory SQLite database for fast, isolated tests.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.main import app

# ── Test database (SQLite in-memory) ─────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Fresh in-memory SQLite database per test."""
    # Import all models so metadata is populated
    from app.models import user, meal, nutrition_cache  # noqa: F401

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db):
    """FastAPI test client with overridden DB and Redis dependencies."""
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_redis] = lambda: None  # Disable Redis in tests

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


# ── Auth helpers ──────────────────────────────────────────────────────────────
TEST_USER = {"email": "test@swaq.app", "name": "Test User", "password": "testpass123"}
TEST_USER_2 = {"email": "other@swaq.app", "name": "Other User", "password": "otherpass456"}


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register a test user and return auth headers."""
    resp = await client.post("/api/v1/auth/register", json=TEST_USER)
    assert resp.status_code == 201, resp.text
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_headers_2(client: AsyncClient) -> dict:
    """Second user's auth headers."""
    resp = await client.post("/api/v1/auth/register", json=TEST_USER_2)
    assert resp.status_code == 201
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def profile_headers(client: AsyncClient, auth_headers: dict) -> dict:
    """Auth headers for a user who also has a profile created."""
    profile_data = {
        "age": 25,
        "gender": "male",
        "height_cm": 175.0,
        "weight_kg": 70.0,
        "activity_level": "moderate",
        "health_goal": "maintain",
    }
    resp = await client.post("/api/v1/profile/", json=profile_data, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return auth_headers
