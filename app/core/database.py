"""
Async SQLAlchemy engine, session factory, and Base for all ORM models.

On Vercel: uses psycopg (psycopg3) driver with pre-resolved DNS.
  Vercel's Lambda sandbox blocks async DNS resolution (uvloop getaddrinfo
  returns EBUSY). We resolve the hostname synchronously at import time
  and pass the IP via psycopg's `hostaddr` parameter to skip async DNS.
Elsewhere: uses asyncpg — faster, no sandbox restrictions.
"""

import logging
import os
import socket
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_IS_VERCEL = "VERCEL" in os.environ


def _resolve_host(hostname: str, port: int) -> str | None:
    """Synchronously resolve hostname to IP. Returns None on failure."""
    try:
        results = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if results:
            ip = results[0][4][0]
            logger.info(f"DNS pre-resolved: {hostname} -> {ip}")
            return ip
    except Exception as exc:
        logger.warning(f"DNS pre-resolve failed for {hostname}: {exc}")
    return None


def _build_db_url(url: str) -> str:
    """Convert a database URL to the correct async driver prefix."""
    if not (url.startswith("postgresql://") or url.startswith("postgres://")):
        return url

    # Normalize to standard prefix
    url = url.replace("postgres://", "postgresql://", 1)

    if _IS_VERCEL:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
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
    from sqlalchemy.pool import NullPool

    engine_kwargs["poolclass"] = NullPool
    logger.info("Vercel detected: Using NullPool + psycopg driver.")
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 1800
    logger.info("Standard environment: Using persistent connection pool.")

# ── Connect args (driver-specific) ──────────────────────────────────────────
if "postgresql" in _db_url:
    if _IS_VERCEL:
        # psycopg3 connect args
        connect_args: dict = {
            "prepare_threshold": 0,  # Required for Supabase transaction-mode pooler
            # SSL is required: Supabase's pooler (Supavisor) uses SSL SNI to route
            # connections to the correct project tenant. Without SSL, auth fails.
            # psycopg handles SSL via Python's ssl module (not uvloop), so this works.
            "sslmode": "require",
        }

        # Pre-resolve DNS synchronously to bypass uvloop's broken async getaddrinfo.
        # psycopg's `hostaddr` parameter tells it to skip DNS and connect to the IP
        # directly, while still using the hostname for SSL SNI.
        parsed = urlparse(_db_url)
        if parsed.hostname:
            resolved_ip = _resolve_host(parsed.hostname, parsed.port or 5432)
            if resolved_ip:
                connect_args["hostaddr"] = resolved_ip
                logger.info(f"Will connect via pre-resolved IP: {resolved_ip}")
            else:
                logger.warning("Could not pre-resolve DB host; async DNS will be attempted.")

        engine_kwargs["connect_args"] = connect_args
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
