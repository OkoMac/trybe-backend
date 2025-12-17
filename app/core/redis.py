"""Redis configuration and connection management"""

from typing import Optional
import redis.asyncio as aioredis
from redis.asyncio import Redis
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client
_redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """Get or create Redis client"""
    global _redis_client

    if _redis_client is None:
        logger.info(f"Creating Redis client: {settings.REDIS_URL.split('@')[-1]}")

        _redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )

        logger.info("Redis client created successfully")

    return _redis_client


async def get_redis() -> Redis:
    """
    Dependency for getting Redis client

    Usage:
        @app.get("/cache")
        async def get_cache(redis: Redis = Depends(get_redis)):
            value = await redis.get("key")
            return {"value": value}
    """
    return await get_redis_client()


async def close_redis() -> None:
    """Close Redis connection"""
    global _redis_client

    if _redis_client is not None:
        logger.info("Closing Redis connection...")
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


async def check_redis_health() -> bool:
    """Check if Redis connection is healthy"""
    try:
        client = await get_redis_client()
        await client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


# Cache helper functions
class CacheService:
    """Redis cache service"""

    def __init__(self):
        self._client: Optional[Redis] = None

    async def _get_client(self) -> Redis:
        """Get Redis client"""
        if self._client is None:
            self._client = await get_redis_client()
        return self._client

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        client = await self._get_client()
        return await client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            expire: Expiration time in seconds
        """
        client = await self._get_client()
        return await client.set(key, value, ex=expire)

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        client = await self._get_client()
        return await client.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        client = await self._get_client()
        return await client.exists(key)

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment value"""
        client = await self._get_client()
        return await client.incrby(key, amount)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for key"""
        client = await self._get_client()
        return await client.expire(key, seconds)

    async def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field"""
        client = await self._get_client()
        return await client.hset(name, key, value)

    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field"""
        client = await self._get_client()
        return await client.hget(name, key)

    async def hgetall(self, name: str) -> dict:
        """Get all hash fields"""
        client = await self._get_client()
        return await client.hgetall(name)


# Global cache service instance
cache = CacheService()
