import logging
import time

from fastapi import Depends, HTTPException, status

from app.auth.deps import get_current_user
from app.core.redis import get_redis
from app.models.user import User

logger = logging.getLogger(__name__)

RATE_LIMIT = 30
WINDOW_SECONDS = 60


async def rate_limit(current_user: User = Depends(get_current_user)) -> None:
    redis = get_redis()
    if redis is None:
        return

    minute_bucket = int(time.time() / WINDOW_SECONDS)
    key = f"ratelimit:{current_user.id}:{minute_bucket}"

    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, WINDOW_SECONDS)

    if count > RATE_LIMIT:
        ttl = await redis.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {RATE_LIMIT} requests per {WINDOW_SECONDS}s",
            headers={
                "Retry-After": str(ttl),
                "X-RateLimit-Limit": str(RATE_LIMIT),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + ttl),
            },
        )
