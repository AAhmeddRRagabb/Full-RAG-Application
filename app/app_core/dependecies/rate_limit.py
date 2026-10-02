from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError


async def check_rate_limit(redis: Redis, key: str, limit: int, window_seconds: int) -> None:
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)

    except RedisError:
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail = "Rate limit service unavailable",
        )

    if count > limit:
        raise HTTPException(
            status_code = status.HTTP_429_TOO_MANY_REQUESTS,
            detail = "Too many requests. Please try again later.",
        )
