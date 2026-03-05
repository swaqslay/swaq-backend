"""
Async SQLAlchemy engine, session factory, and Base for all ORM models.

On Vercel: uses a SYNC psycopg3 engine running in threads.
  Vercel's Lambda sandbox blocks uvloop's create_connection (EBUSY),
  which breaks all async PostgreSQL drivers. Django works on Vercel
  because it uses sync (blocking) connections. We do the same —
  sync psycopg3 connections in a thread pool, wrapped in an async
  interface so all existing await db.execute(...) code works unchanged.
Elsewhere: uses asyncpg natively — fastest async PostgreSQL driver.
"""

import asyncio
import logging
import os
from functools import partial

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_IS_VERCEL = "VERCEL" in os.environ


def _normalize_url(url: str) -> str:
    """Normalize postgres:// to postgresql://."""
    return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# ═════════════════════════════════════════════════════════════════════════════
# VERCEL PATH: Sync psycopg3 engine + async wrapper
# ═════════════════════════════════════════════════════════════════════════════

if _IS_VERCEL:
    from sqlalchemy.pool import NullPool

    _sync_url = _normalize_url(settings.database_url).replace(
        "postgresql://", "postgresql+psycopg://", 1
    )
    host_part = _sync_url.split("@")[-1] if "@" in _sync_url else _sync_url
    logger.info("ENVIRONMENT: Vercel serverless")
    logger.info(f"DATABASE: PostgreSQL (Supabase) Host: {host_part} Driver: psycopg (sync-in-thread)")

    _sync_engine = create_engine(
        _sync_url,
        echo=False,
        poolclass=NullPool,
        connect_args={
            "prepare_threshold": 0,  # Supabase transaction-mode pooler
            "sslmode": "require",
        },
    )
    _SyncSessionLocal = sessionmaker(bind=_sync_engine, expire_on_commit=False)

    class _SyncToAsyncSession:
        """Wraps a sync Session to provide the async interface our code expects.

        All blocking DB operations run in the default thread-pool executor,
        completely bypassing uvloop's broken create_connection.
        """

        def __init__(self, sync_session: Session) -> None:
            self._s = sync_session

        async def _run(self, fn, *args, **kwargs):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

        async def execute(self, *args, **kwargs):
            return await self._run(self._s.execute, *args, **kwargs)

        async def flush(self, *args, **kwargs):
            return await self._run(self._s.flush, *args, **kwargs)

        async def commit(self):
            return await self._run(self._s.commit)

        async def rollback(self):
            return await self._run(self._s.rollback)

        async def refresh(self, instance, *args, **kwargs):
            return await self._run(self._s.refresh, instance, *args, **kwargs)

        async def delete(self, instance):
            return await self._run(self._s.delete, instance)

        async def close(self):
            return await self._run(self._s.close)

        def add(self, instance):
            """add() is in-memory only, no I/O needed."""
            self._s.add(instance)

    async def get_db():
        """Yield an async-wrapped sync session for Vercel."""
        sync_session = _SyncSessionLocal()
        db = _SyncToAsyncSession(sync_session)
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()

    async def init_db() -> None:
        """Verify DB connection using sync engine in a thread."""
        loop = asyncio.get_event_loop()
        def _check():
            with _sync_engine.connect() as conn:
                conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        await loop.run_in_executor(None, _check)
        logger.info("Database connection verified (sync-in-thread).")


# ═════════════════════════════════════════════════════════════════════════════
# STANDARD PATH: Native async engine with asyncpg
# ═════════════════════════════════════════════════════════════════════════════

else:
    _async_url = _normalize_url(settings.database_url).replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
    host_part = _async_url.split("@")[-1] if "@" in _async_url else _async_url
    logger.info("ENVIRONMENT: Standard system")
    logger.info(f"DATABASE: PostgreSQL (Supabase) Host: {host_part} Driver: asyncpg")

    _engine_kwargs: dict = {
        "echo": (not settings.is_production),
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }

    if "postgresql" in _async_url:
        import ssl

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        _engine_kwargs["connect_args"] = {
            "statement_cache_size": 0,
            "ssl": ssl_context,
        }

    engine = create_async_engine(_async_url, **_engine_kwargs)

    _async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def get_db():
        """Yield a native async session."""
        async with _async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def init_db() -> None:
        """Verify DB connection using async engine."""
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("Database connection verified.")
