from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.core.config import settings

# 연결 풀은 앱 전체에서 하나를 공유, 종료 시 main의 lifespan에서 닫음
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> Redis:
    return redis_client


RedisDep = Annotated[Redis, Depends(get_redis)]
