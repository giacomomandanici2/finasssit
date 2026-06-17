from fastapi import FastAPI

from app.api.agent import router as agent_router
from app.api.kb import router as kb_router
from app.api.rag import router as rag_router
from app.api.transactions import router as transactions_router
from app.api.v1 import router as v1_router
from app.auth.router import router as auth_router
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
