from fastapi import FastAPI

from app.api.transactions import router as transactions_router
from app.api.v1 import router as v1_router
from app.core.lifespan import lifespan


app = FastAPI(
    title="FinAssist AI",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(transactions_router)
app.include_router(v1_router)
