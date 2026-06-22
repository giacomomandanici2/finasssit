from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.agent import router as agent_router
from app.api.kb import router as kb_router
from app.api.rag import router as rag_router
from app.api.transactions import router as transactions_router
from app.api.v1 import router as v1_router
from app.auth.router import router as auth_router
from app.core.db import engine
from app.core.lifespan import lifespan


app = FastAPI(
    title="FinAssist AI",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(transactions_router)
app.include_router(v1_router)
app.include_router(kb_router)
app.include_router(auth_router)
app.include_router(rag_router)
app.include_router(agent_router)


@app.get("/health")
async def liveness():
    return JSONResponse({"status": "alive"})


@app.get("/ready")
async def readiness():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse({"status": "ready", "database": "ok"})
    except Exception as exc:
        return JSONResponse(
            {"status": "not ready", "database": str(exc)},
            status_code=503,
        )
