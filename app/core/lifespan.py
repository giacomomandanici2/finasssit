import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from opentelemetry import trace

from app.core.config import settings
from app.core.db import engine
from app.core.otel import setup_otel
from app.core.redis import close_redis, init_redis

logger = logging.getLogger(__name__)

_SHUTDOWN_TIMEOUT = 10  # seconds


async def _shutdown_with_timeout(coro, name: str):
    try:
        await asyncio.wait_for(coro, timeout=_SHUTDOWN_TIMEOUT)
        logger.info("[shutdown] %s closed gracefully", name)
    except TimeoutError:
        logger.warning("[shutdown] %s forced close after timeout", name)
    except Exception as exc:
        logger.warning("[shutdown] %s close error: %s", name, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("[startup] FinAssist starting...")
    setup_otel(app)
    try:
        await init_redis(settings.redis_url)
    except Exception:
        logger.warning("[startup] Redis unavailable — proceeding without cache")

    yield

    logger.info("[shutdown] FinAssist shutting down...")

    await _shutdown_with_timeout(engine.dispose(), "SQLAlchemy engine")
    await _shutdown_with_timeout(close_redis(), "Redis pool")

    provider = trace.get_tracer_provider()
    if hasattr(provider, "shutdown"):
        try:
            await asyncio.wait_for(
                asyncio.to_thread(provider.shutdown),
                timeout=_SHUTDOWN_TIMEOUT,
            )
            logger.info("[shutdown] OTel tracer closed gracefully")
        except TimeoutError:
            logger.warning("[shutdown] OTel tracer forced close after timeout")
        except Exception as exc:
            logger.warning("[shutdown] OTel tracer close error: %s", exc)

    logger.info("[shutdown] done")
