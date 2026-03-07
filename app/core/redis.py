"""
Redis connection pool using redis.asyncio.
Provides an async context manager and a global client for the app lifespan.
"""

import logging

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level client — initialized in app lifespan
_redis_client: aioredis.Redis | None = None


async def init_redis() -> None:
    """Initialize the Redis connection pool. Called on app startup."""
    global _redis_client
    if not settings.redis_url:
        logger.warning("REDIS_URL not set — caching disabled. Set REDIS_URL for production.")
        return
    try:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        # Test connection
        await _redis_client.ping()
        logger.info("Redis connected successfully.")
    except Exception as exc:
        logger.warning(f"Redis connection failed: {exc}. Caching disabled.")
        _redis_client = None


async def close_redis() -> None:
    """Close the Redis connection pool. Called on app shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed.")


def get_redis() -> aioredis.Redis | None:
    """
    FastAPI dependency: yields the Redis client (or None if unavailable).
    Services must handle None gracefully — Redis is optional for correctness,
    only mandatory for performance.
    """
    return _redis_client
