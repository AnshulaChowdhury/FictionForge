"""
Redis Client for caching (Epic 5B).

Provides a simple interface for caching world rule retrieval results
with automatic TTL management.
"""

import json
import logging
from typing import Optional, Any
from redis import asyncio as aioredis
from redis.exceptions import RedisError
from api.config import get_settings

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """
    Get or create Redis client connection.

    Returns:
        Redis client instance

    Raises:
        RedisError: If connection fails
    """
    global _redis_client

    if _redis_client is None:
        settings = get_settings()

        try:
            _redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )

            # Test connection
            await _redis_client.ping()
            logger.info(f"Connected to Redis at {settings.redis_url}")

        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            _redis_client = None
            raise

    return _redis_client


async def close_redis_client():
    """Close the Redis client connection."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Closed Redis connection")


class RedisCache:
    """
    Simple Redis cache wrapper with JSON serialization.

    Usage:
        cache = RedisCache()
        await cache.set("key", {"data": "value"}, ttl=900)
        result = await cache.get("key")
    """

    def __init__(self):
        """Initialize RedisCache."""
        self.settings = get_settings()
        self.default_ttl = self.settings.redis_ttl_seconds  # 900 seconds (15 minutes)

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Deserialized value or None if not found or error
        """
        try:
            client = await get_redis_client()
            value = await client.get(key)

            if value is not None:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)

            logger.debug(f"Cache miss: {key}")
            return None

        except RedisError as e:
            logger.warning(f"Redis get error for key {key}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting cache key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (defaults to 900s/15min)

        Returns:
            True if successful, False otherwise
        """
        try:
            client = await get_redis_client()
            ttl = ttl if ttl is not None else self.default_ttl

            serialized = json.dumps(value)
            await client.setex(key, ttl, serialized)

            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
            return True

        except RedisError as e:
            logger.warning(f"Redis set error for key {key}: {e}")
            return False
        except json.JSONEncodeError as e:
            logger.error(f"JSON encode error for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting cache key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            client = await get_redis_client()
            result = await client.delete(key)

            logger.debug(f"Cache delete: {key} (existed: {result > 0})")
            return result > 0

        except RedisError as e:
            logger.warning(f"Redis delete error for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting cache key {key}: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Useful for cache invalidation (e.g., "rules:book_id:*")

        Args:
            pattern: Key pattern (e.g., "rules:*")

        Returns:
            Number of keys deleted
        """
        try:
            client = await get_redis_client()

            # Scan for keys matching pattern
            keys_to_delete = []
            async for key in client.scan_iter(match=pattern, count=100):
                keys_to_delete.append(key)

            if keys_to_delete:
                deleted = await client.delete(*keys_to_delete)
                logger.info(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted

            return 0

        except RedisError as e:
            logger.warning(f"Redis delete pattern error for {pattern}: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error deleting pattern {pattern}: {e}")
            return 0

    async def invalidate_trilogy_rules(self, trilogy_id: str) -> int:
        """
        Invalidate all cached rules for a trilogy.

        Called when rules are updated or book associations change.

        Args:
            trilogy_id: Trilogy identifier

        Returns:
            Number of keys deleted
        """
        pattern = f"rules:*:{trilogy_id}:*"
        return await self.delete_pattern(pattern)

    async def invalidate_book_rules(self, book_id: str) -> int:
        """
        Invalidate all cached rules for a specific book.

        Called when book-specific rules are updated.

        Args:
            book_id: Book identifier

        Returns:
            Number of keys deleted
        """
        pattern = f"rules:{book_id}:*"
        return await self.delete_pattern(pattern)


# Singleton instance for convenience
redis_cache = RedisCache()
