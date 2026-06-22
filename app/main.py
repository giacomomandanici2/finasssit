import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.agent import router as agent_router
from app.api.kb import router as kb_router
from app.api.rag import router as rag_router
from app.api.transactions import router as transactions_router
from app.api.v1 import router as v1_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.db import engine
from app.core.lifespan import lifespan
from app.core.log_context import extract_log_context, setup_logging
from app.core.redis import get_redis
from app.core.slowrate import limiter

logger = logging.getLogger(__name__)

setup_logging()


app = FastAPI(
    title="FinAssist AI",
    version="0.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def log_context_middleware(request, call_next):
    extract_log_context(request)
    response = await call_next(request)
    return response


app.include_router(transactions_router)
app.include_router(v1_router)
app.include_router(kb_router)
app.include_router(auth_router)
app.include_router(rag_router)
app.include_router(agent_router)


@app.get("/health/live")
@limiter.exempt
async def liveness():
    return JSONResponse({"status": "alive"})


@app.get("/health/ready")
@limiter.exempt
async def readiness():
    checks: dict[str, str | bool] = {}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = str(exc)

    redis_client = get_redis()
    if redis_client is not None:
        try:
            await redis_client.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = str(exc)
    else:
        checks["redis"] = "skipped (not configured)"

    if settings.azure_openai_endpoint:
        try:
            from openai import AsyncAzureOpenAI
            client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )
            await client.models.list()
            checks["azure_openai"] = "ok"
        except Exception as exc:
            checks["azure_openai"] = str(exc)
    else:
        checks["azure_openai"] = "skipped (not configured)"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ready" if all_ok else "degraded", "checks": checks},
        status_code=200 if all_ok else 503,
    )
