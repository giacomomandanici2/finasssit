from fastapi import FastAPI

from app.api.transactions import router as transactions_router
from app.core.lifespan import lifespan


app = FastAPI(
    title="FinAssist AI",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(transactions_router)
