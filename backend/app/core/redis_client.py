"""Redis connection pool for session and cache storage."""
import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()

_pool: Optional[aioredis.ConnectionPool] = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = aioredis.ConnectionPool.from_url(
            settings.redis_url, decode_responses=True, max_connections=20
        )
    return _pool


def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_redis_pool())


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    r = get_redis()
    await r.setex(key, ttl, json.dumps(value))


async def cache_get(key: str) -> Optional[Any]:
    r = get_redis()
    raw = await r.get(key)
    return json.loads(raw) if raw else None


async def cache_delete(key: str) -> None:
    r = get_redis()
    await r.delete(key)
