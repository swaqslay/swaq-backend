"""
Async SQLAlchemy engine, session factory, and Base for all ORM models.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_db_url(url: str) -> str:
    """Ensure async driver prefix is used."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        # Common Heroku/Railway format
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


import os

_db_url = _build_db_url(settings.database_url)

# ── Vercel Workaround ────────────────────────────────────────────────────────
# Vercel has a read-only filesystem EXCEPT for /tmp.
# If we are on Vercel and using SQLite, redirect the DB file to /tmp.
if "VERCEL" in os.environ and _db_url.startswith("sqlite"):
    _db_url = "sqlite+aiosqlite:////tmp/swaq.db"
    logger.info(f"Vercel detected: Redirecting SQLite to {_db_url}")

engine = create_async_engine(
    _db_url,
    echo=(settings.app_env == "development"),
    pool_pre_ping=True,   # Detect stale connections
    pool_recycle=1800,    # Recycle connections every 30 min
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI dependency: yields a DB session per request.
    Auto-commits on success, rolls back on exception.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Create all tables from metadata.
    Only used for local dev / SQLite.
    In production, use Alembic migrations: `alembic upgrade head`.
    """
    # Import models here so their metadata is registered on Base before create_all
    from app.models import user, meal, nutrition_cache  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized.")
