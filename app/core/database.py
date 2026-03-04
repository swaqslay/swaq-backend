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

# ── Database Connection Verification ──────────────────────────────────────────
# Log the environment for debugging
if "VERCEL" in os.environ:
    logger.info("ENVIRONMENT: Vercel serverless (Production)")
else:
    logger.info("ENVIRONMENT: Standard system")

if not _db_url.startswith("postgresql"):
    logger.error(f"INVALID DATABASE TYPE: Only PostgreSQL/Supabase is supported. URL: {_db_url.split('://')[0]}://...")
else:
    logger.info(f"DATABASE DETECTED: PostgreSQL (Supabase) Host: {_db_url.split('@')[-1] if '@' in _db_url else _db_url}")

engine_kwargs = {
    "echo": (not settings.is_production),
    "pool_pre_ping": True,
    "pool_recycle": 1800,
    "prepared_statement_cache_size": 0,  # Correct location for SQLAlchemy asyncpg
}

# Vercel has short-lived functions. Pooling is better disabled to avoid "resource busy" errors.
if "VERCEL" in os.environ:
    from sqlalchemy.pool import NullPool
    engine_kwargs["poolclass"] = NullPool
    logger.info("Vercel detected: Using NullPool for serverless environment.")
else:
    logger.info("Standard environment: Using persistent connection pool.")

# Supabase Pooler (Transaction Mode) requires disabling prepared statements.
# Using a relaxed SSL context to avoid certificate verification errors on some systems.
if "postgresql" in _db_url:
    import ssl
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    engine_kwargs["connect_args"] = {
        "statement_cache_size": 0,  # Direct asyncpg argument
        "ssl": ssl_context
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
    Initialize database connection.
    Table creation is handled by Alembic migrations.
    """
    # Simply verify connection
    async with engine.connect() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    logger.info("Database connection verified.")
