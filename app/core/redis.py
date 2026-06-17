import logging

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_client: Redis | None = None


async def init_redis(url: str) -> None:
    global _client
    _client = Redis.from_url(url, decode_responses=True)
    await _client.ping()
    logger.info("Redis connected: %s", url)


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("Redis disconnected")


def get_redis() -> Redis | None:
    return _client
