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
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1).replace("postgres://", "postgresql+asyncpg://", 1)
    return url


import os

_db_url = _build_db_url(settings.database_url)

# ── Vercel Workaround ────────────────────────────────────────────────────────
# Log the environment for debugging
if "VERCEL" in os.environ:
    logger.info("ENVIRONMENT: Vercel serverless (Production)")
    # Vercel has a read-only filesystem. SQLite is for LOCAL ONLY.
    if _db_url.startswith("sqlite"):
         logger.warning(f"DATABASE DETECTED: SQLite (Caution: Read-only filesystem!) URL: {_db_url}")
    else:
        logger.info(f"DATABASE DETECTED: PostgreSQL (Supabase) Host: {_db_url.split('@')[-1] if '@' in _db_url else _db_url}")
else:
    logger.info(f"ENVIRONMENT: Standard system. DB: {_db_url.split('@')[-1] if '@' in _db_url else _db_url}")

# Database engine configuration
engine_kwargs = {
    "echo": (not settings.is_production),
    "pool_pre_ping": True,
    "pool_recycle": 1800,
}

# Vercel has short-lived functions. Pooling is better disabled to avoid "resource busy" errors.
if "VERCEL" in os.environ:
    from sqlalchemy.pool import NullPool
    engine_kwargs["poolclass"] = NullPool
    logger.info("Vercel detected: Using NullPool for serverless environment.")
else:
    logger.info("Standard environment: Using persistent connection pool.")

# Supabase Pooler (Transaction Mode) requires disabling prepared statements.
# Using ssl=True is standard for asyncpg to require SSL.
if "postgresql" in _db_url:
    engine_kwargs["connect_args"] = {
        "prepared_statement_cache_size": 0,
        "ssl": True
    }

engine = create_async_engine(_db_url, **engine_kwargs)

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
    Initialize database tables. 
    Only runs create_all for SQLite.
    For Postgres, use Alembic: `alembic upgrade head`.
    """
    # Import models here so their metadata is registered on Base before create_all
    from app.models import user, meal, nutrition_cache  # noqa: F401

    # Only run create_all for SQLite (local dev without Alembic)
    if _db_url.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite tables initialized.")
    else:
        logger.info("PostgreSQL detected: Skipping automatic table creation (use Alembic).")
