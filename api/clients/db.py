import os
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JOB_KEY_PREFIX = "derridai:job:"
JOB_TTL_SECONDS = 60 * 60 * 24

class RedisClient:
    redis: Redis
    def __init__(self):
        self.job_key_prefix: str = JOB_KEY_PREFIX
        self.redis = Redis.from_url(REDIS_URL, decode_responses=True)

    async def get(self, key: str) -> str | None:
        key = f"{self.job_key_prefix}{key}"
        r = await self.redis.get(key)
        return str(r) if r is not None else None

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        key = f"{self.job_key_prefix}{key}"
        await self.redis.set(key, value, ex=ex)