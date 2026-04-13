import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True)
    return _redis


async def get_cached_assets(company_id: str) -> Optional[dict]:
    try:
        r = await get_redis()
        data = await r.get(f"assets:{company_id}")
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
    return None


async def set_cached_assets(company_id: str, data: dict):
    try:
        r = await get_redis()
        await r.set(f"assets:{company_id}", json.dumps(data, default=str), ex=settings.REDIS_TTL_SECONDS)
    except Exception as e:
        logger.warning(f"Redis set error: {e}")


async def invalidate_cache(company_id: str):
    try:
        r = await get_redis()
        await r.delete(f"assets:{company_id}")
    except Exception as e:
        logger.warning(f"Redis delete error: {e}")
