"""
Async SQLAlchemy engine, session factory, and Base for all ORM models.

On Vercel: uses psycopg (psycopg3) driver — compatible with uvloop sandbox.
Elsewhere: uses asyncpg — faster, but incompatible with Vercel's restricted runtime.
"""

import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_IS_VERCEL = "VERCEL" in os.environ


def _build_db_url(url: str) -> str:
    """Convert a database URL to the correct async driver prefix."""
    if not (url.startswith("postgresql://") or url.startswith("postgres://")):
        return url

    # Normalize to standard prefix
    url = url.replace("postgres://", "postgresql://", 1)

    if _IS_VERCEL:
        # psycopg3 async driver — works on Vercel
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
        # asyncpg — faster, used locally and on standard hosts
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)


_db_url = _build_db_url(settings.database_url)

# ── Logging ──────────────────────────────────────────────────────────────────
if _IS_VERCEL:
    logger.info("ENVIRONMENT: Vercel serverless (Production)")
else:
    logger.info("ENVIRONMENT: Standard system")

if not _db_url.startswith("postgresql"):
    logger.error(
        "INVALID DATABASE TYPE: Only PostgreSQL/Supabase is supported. "
        f"URL: {_db_url.split('://')[0]}://..."
    )
else:
    host_part = _db_url.split("@")[-1] if "@" in _db_url else _db_url
    driver = "psycopg" if "+psycopg" in _db_url else "asyncpg"
    logger.info(f"DATABASE DETECTED: PostgreSQL (Supabase) Host: {host_part} Driver: {driver}")

# ── Engine kwargs ────────────────────────────────────────────────────────────
engine_kwargs: dict = {
    "echo": (not settings.is_production),
}

if _IS_VERCEL:
    # Serverless: no persistent pool, each invocation creates/destroys connections
    from sqlalchemy.pool import NullPool

    engine_kwargs["poolclass"] = NullPool
    logger.info("Vercel detected: Using NullPool + psycopg driver.")
else:
    # Standard: persistent pool with health checks
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 1800
    logger.info("Standard environment: Using persistent connection pool.")

# ── Connect args (driver-specific) ──────────────────────────────────────────
if "postgresql" in _db_url:
    if _IS_VERCEL:
        # psycopg3 connect args
        # Supabase pooler (transaction mode) doesn't support prepared statements
        engine_kwargs["connect_args"] = {
            "prepare_threshold": 0,
        }
    else:
        # asyncpg connect args
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        engine_kwargs["connect_args"] = {
            "statement_cache_size": 0,
            "ssl": ssl_context,
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
    async with engine.connect() as conn:
        await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    logger.info("Database connection verified.")
