"""Redis caching layer."""

import json
from typing import Any, Optional

import redis
from redis.connection import ConnectionPool

from backend.core.config import get_settings

settings = get_settings()


class RedisCache:
    """Redis cache client with connection pooling."""

    def __init__(self):
        """Initialize Redis cache with connection pool."""
        self.pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
        self.client = redis.Redis(connection_pool=self.pool)

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            value = self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (redis.RedisError, json.JSONDecodeError):
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = json.dumps(value)
            return self.client.setex(key, ttl, serialized)
        except (redis.RedisError, TypeError):
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        try:
            return self.client.delete(key) > 0
        except redis.RedisError:
            return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        try:
            return self.client.exists(key) > 0
        except redis.RedisError:
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "session:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except redis.RedisError:
            return 0

    def ping(self) -> bool:
        """
        Check if Redis is available.

        Returns:
            True if available, False otherwise
        """
        try:
            return self.client.ping()
        except (redis.RedisError, Exception):
            return False


# Cache key prefixes and TTLs
CACHE_TTL_SESSION_STATE = 900  # 15 minutes
CACHE_TTL_TECHNICIAN_SCHEDULE = 900  # 15 minutes
CACHE_TTL_CUSTOMER_DATA = 3600  # 1 hour
CACHE_TTL_PARTS_INVENTORY = 300  # 5 minutes


class CacheManager:
    """High-level cache manager with domain-specific methods."""

    def __init__(self, cache: RedisCache):
        """Initialize cache manager."""
        self.cache = cache

    # Session state caching
    def get_session_state(self, session_id: str) -> Optional[dict]:
        """Get session state from cache."""
        return self.cache.get(f"session:{session_id}")

    def set_session_state(self, session_id: str, state: dict) -> bool:
        """Set session state in cache (15 min TTL)."""
        return self.cache.set(f"session:{session_id}", state, CACHE_TTL_SESSION_STATE)

    def delete_session_state(self, session_id: str) -> bool:
        """Delete session state from cache."""
        return self.cache.delete(f"session:{session_id}")

    # Technician schedule caching
    def get_technician_schedule(self, technician_id: str) -> Optional[dict]:
        """Get technician schedule from cache."""
        return self.cache.get(f"schedule:technician:{technician_id}")

    def set_technician_schedule(self, technician_id: str, schedule: dict) -> bool:
        """Set technician schedule in cache (15 min TTL)."""
        return self.cache.set(
            f"schedule:technician:{technician_id}",
            schedule,
            CACHE_TTL_TECHNICIAN_SCHEDULE,
        )

    def invalidate_technician_schedule(self, technician_id: str) -> bool:
        """Invalidate technician schedule cache."""
        return self.cache.delete(f"schedule:technician:{technician_id}")

    def invalidate_all_schedules(self) -> int:
        """Invalidate all technician schedules."""
        return self.cache.clear_pattern("schedule:technician:*")

    # Customer data caching
    def get_customer_data(self, customer_id: str) -> Optional[dict]:
        """Get customer data from cache."""
        return self.cache.get(f"customer:{customer_id}")

    def set_customer_data(self, customer_id: str, data: dict) -> bool:
        """Set customer data in cache (1 hour TTL)."""
        return self.cache.set(f"customer:{customer_id}", data, CACHE_TTL_CUSTOMER_DATA)

    def invalidate_customer_data(self, customer_id: str) -> bool:
        """Invalidate customer data cache."""
        return self.cache.delete(f"customer:{customer_id}")

    # Parts inventory caching
    def get_part_inventory(self, part_id: str) -> Optional[dict]:
        """Get part inventory from cache."""
        return self.cache.get(f"part:inventory:{part_id}")

    def set_part_inventory(self, part_id: str, inventory: dict) -> bool:
        """Set part inventory in cache (5 min TTL)."""
        return self.cache.set(
            f"part:inventory:{part_id}",
            inventory,
            CACHE_TTL_PARTS_INVENTORY,
        )

    def invalidate_part_inventory(self, part_id: str) -> bool:
        """Invalidate part inventory cache."""
        return self.cache.delete(f"part:inventory:{part_id}")

    def invalidate_all_parts(self) -> int:
        """Invalidate all parts inventory cache."""
        return self.cache.clear_pattern("part:inventory:*")

    # Conversation context caching
    def get_conversation_context(self, conversation_id: str) -> Optional[dict]:
        """Get conversation context from cache."""
        return self.cache.get(f"conversation:context:{conversation_id}")

    def set_conversation_context(self, conversation_id: str, context: dict) -> bool:
        """Set conversation context in cache (15 min TTL)."""
        return self.cache.set(
            f"conversation:context:{conversation_id}",
            context,
            CACHE_TTL_SESSION_STATE,
        )

    def delete_conversation_context(self, conversation_id: str) -> bool:
        """Delete conversation context from cache."""
        return self.cache.delete(f"conversation:context:{conversation_id}")


# Global cache instances
_redis_cache: Optional[RedisCache] = None
_cache_manager: Optional[CacheManager] = None


def get_redis_cache() -> RedisCache:
    """Get global Redis cache instance."""
    global _redis_cache
    if _redis_cache is None:
        _redis_cache = RedisCache()
    return _redis_cache


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(get_redis_cache())
    return _cache_manager
