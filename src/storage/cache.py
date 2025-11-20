"""Redis cache configuration and utilities."""

import redis.asyncio as redis
import json
import logging
from typing import Any, Optional

from src.config import settings

logger = logging.getLogger(__name__)

# Global cache client
_cache_client: Optional[redis.Redis] = None


async def init_cache() -> None:
    """Initialize Redis cache connection."""
    global _cache_client

    logger.info("Initializing Redis cache connection")
    _cache_client = redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.redis_pool_size,
    )

    # Test connection
    await _cache_client.ping()
    logger.info("Redis cache initialized successfully")


async def get_cache() -> redis.Redis:
    """
    Get Redis cache client.

    Returns:
        redis.Redis: Cache client

    Raises:
        RuntimeError: If cache not initialized
    """
    if _cache_client is None:
        raise RuntimeError("Cache not initialized. Call init_cache() first.")
    return _cache_client


async def cache_get(key: str) -> Optional[Any]:
    """
    Get value from cache.

    Args:
        key: Cache key

    Returns:
        Cached value or None if not found
    """
    cache = await get_cache()
    value = await cache.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """
    Set value in cache.

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds (default: from settings)
    """
    cache = await get_cache()
    ttl = ttl or settings.redis_cache_ttl

    if isinstance(value, (dict, list)):
        value = json.dumps(value)

    await cache.setex(key, ttl, value)


async def cache_delete(key: str) -> None:
    """
    Delete value from cache.

    Args:
        key: Cache key
    """
    cache = await get_cache()
    await cache.delete(key)


async def cache_exists(key: str) -> bool:
    """
    Check if key exists in cache.

    Args:
        key: Cache key

    Returns:
        True if key exists, False otherwise
    """
    cache = await get_cache()
    return await cache.exists(key) > 0
