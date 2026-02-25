import redis.asyncio as redis
import json
import hashlib
from typing import Optional, Any
from functools import wraps
from app.config import settings


class CacheService:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        await self.redis.setex(key, ttl, json.dumps(value))

    async def delete(self, key: str):
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str):
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)


cache_service = CacheService(settings.REDIS_URL)


def cached(ttl: int = 3600, key_prefix: str = ""):
    """缓存装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键 (简单实现，仅针对可 JSON 序列化的参数)
            key_data = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # 尝试从缓存获取
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 执行原函数
            result = await func(*args, **kwargs)

            # 存入缓存
            await cache_service.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator
