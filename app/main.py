"""Entry point dell'agent service FinAssist AI."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.transactions import router as transactions_router #import del router per gli endpoint /transactions
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.middleware import request_id_and_access_log
from fastapi.middleware.cors import CORSMiddleware


# per il lifespan, non facciamo altro che eseguire un qualcosa prima di tutto all'avvio
@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    settings = get_settings()
    app.state.settings = settings

    print("🚀 FinAssist AI starting...")

    # qui in futuro: DB, LLM client, cache, ecc.
    # app.state.db = create_engine(...)
    # app.state.llm = OpenAIClient(...)

    yield  # <-- server running

    # SHUTDOWN
    print("🛑 FinAssist AI shutting down")

    # cleanup
    # await app.state.db.close()

app = FastAPI(
    title="FinAssist AI Agent Service",
    description="Backend Python/FastAPI per FinBank S.p.A.",
    version="0.1.0",
    lifespan=lifespan
)
register_exception_handlers(app) #registrazione degli exception handler globali
app.include_router(transactions_router)
app.middleware("http")(request_id_and_access_log) # collegamento middleware in main


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/health") #endpoint standard per verificare lo stato del be su /health
async def health() -> dict[str, str]:
    return {"status": "ok"}

