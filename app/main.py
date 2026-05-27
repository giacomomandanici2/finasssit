"""Entry point dell'agent service FinAssist AI."""
from fastapi import FastAPI
from app.api.transactions import router as transactions_router #import del router per gli endpoint /transactions
from app.core.error_handlers import register_exception_handlers

app = FastAPI(
    title="FinAssist AI Agent Service",
    description="Backend Python/FastAPI per FinBank S.p.A.",
    version="0.1.0",
)
register_exception_handlers(app) #registrazione degli exception handler globali
app.include_router(transactions_router)



@app.get("/health") #endpoint standard per verificare lo stato del be su /health
async def health() -> dict[str, str]:
    return {"status": "ok"}

