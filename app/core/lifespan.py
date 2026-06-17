from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.db import engine
from app.core.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("[startup] FinAssist starting...")
    try:
        await init_redis(settings.redis_url)
    except Exception:
        print("[startup] Redis unavailable — proceeding without cache")

    yield

    print("[shutdown] Closing database connections...")
    await engine.dispose()
    await close_redis()
