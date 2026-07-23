# app/services/cache_service.py
import json
import hashlib
from typing import Optional, Any
import redis.asyncio as aioredis
from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CacheService:
    def __init__(self):
        self.redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
        self.ttl = settings.CACHE_TTL_SECONDS

    def _make_key(self, raw_key: str) -> str:
        """Hash the key to ensure consistent length and encoding."""
        return f"route_ai:{hashlib.md5(raw_key.lower().encode()).hexdigest()}"

    async def get(self, key: str) -> Optional[dict]:
        """Retrieve cached response. Returns None on miss or error."""
        try:
            hashed = self._make_key(key)
            value = await self.redis.get(hashed)
            if value:
                logger.info(f"Cache HIT for key: {key[:50]}")
                return json.loads(value)
            logger.info(f"Cache MISS for key: {key[:50]}")
            return None
        except Exception as e:
            logger.warning(f"Cache GET error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store response in cache with TTL."""
        try:
            hashed = self._make_key(key)
            serialized = json.dumps(value, default=str)
            await self.redis.setex(hashed, ttl or self.ttl, serialized)
            logger.info(f"Cache SET for key: {key[:50]} (TTL: {ttl or self.ttl}s)")
            return True
        except Exception as e:
            logger.warning(f"Cache SET error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Manually invalidate a cache entry."""
        try:
            hashed = self._make_key(key)
            await self.redis.delete(hashed)
            return True
        except Exception as e:
            logger.warning(f"Cache DELETE error: {e}")
            return False

    async def flush_all(self) -> bool:
        """Clear entire cache (use with caution)."""
        try:
            await self.redis.flushdb()
            logger.warning("Cache FLUSHED")
            return True
        except Exception as e:
            logger.error(f"Cache FLUSH error: {e}")
            return False

    async def close(self):
        await self.redis.aclose()