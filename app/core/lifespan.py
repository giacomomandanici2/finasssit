from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import engine

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("🚀 FinAssist starting...")

    yield

    print("🛑 Closing database connections...")

    await engine.dispose()