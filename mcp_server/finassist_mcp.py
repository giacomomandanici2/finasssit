"""FinAssist MCP Server — Espone strumenti finanziari via MCP.

Transport: HTTP+SSE su porta 8001.
"""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Context

from app.core.db import SessionLocal
from app.agents.tools import make_get_saldo, _MOCK_SALDI, _USER_IBANS
from app.rag.service import RAGService

logger = logging.getLogger(__name__)

_LOADED_POLICIES: dict[str, str] = {}
_RATE_LIMIT: dict[str, int] = {}


def _load_policies() -> dict[str, str]:
    return {
        "aml": (
            "Antiriciclaggio (AML) Policy:\n"
            "- Importi > EUR 10.000 richiedono verifica AML obbligatoria.\n"
            "- Paesi ad alto rischio (Iran, Corea del Nord, Siria, Cuba, Myanmar) "
            "richiedono approvazione compliance.\n"
            "- Segnalare operazioni sospette entro 24h."
        ),
        "kyc": (
            "Know Your Customer (KYC) Policy:\n"
            "- Verifica identità obbligatoria all'apertura del conto.\n"
            "- Documento d'identità valido e autodichiarazione.\n"
            "- Aggiornamento dati ogni 12 mesi."
        ),
        "privacy": (
            "Privacy Policy:\n"
            "- I dati personali sono trattati secondo GDPR.\n"
            "- I dati non vengono condivisi con terze parti senza consenso esplicito.\n"
            "- Diritto di rettifica e cancellazione."
        ),
        "whistleblowing": (
            "Whistleblowing Policy:\n"
            "- Canale di segnalazione interno per il personale.\n"
            "- Segnalazioni anonime possibili tramite piattaforma dedicata.\n"
            "- Tutela del segnalante contro eventuali ritorsioni."
        ),
    }


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[None]:
    global _LOADED_POLICIES, _RATE_LIMIT
    _LOADED_POLICIES = _load_policies()
    _RATE_LIMIT = {}
    logger.info("MCP server FinAssist avviato — %d policy caricate", len(_LOADED_POLICIES))
    yield


mcp = FastMCP(
    "FinAssist",
    instructions=(
        "Server MCP per operazioni bancarie e compliance. "
        "Fornisce accesso a saldi, policy, e classificazione transazioni."
    ),
    lifespan=lifespan,
)


def _resolve_user(ctx: Context) -> str | None:
    if ctx.meta and "user_id" in ctx.meta:
        return ctx.meta["user_id"]
    return os.getenv("MCP_USER_ID")


# ── Tools ─────────────────────────────────────

@mcp.tool()
async def get_saldo(iban: str, ctx: Context) -> dict:
    """Ottiene il saldo corrente per un IBAN intestato all'utente autenticato."""
    user_id = _resolve_user(ctx)
    if user_id is None:
        return {"error": "Autenticazione richiesta — fornisci user_id nel contesto"}
    tool = make_get_saldo(user_id)
    result = await tool(iban=iban)
    owned = _USER_IBANS.get(user_id, [])
    iban_clean = iban.strip().replace(" ", "")
    if iban_clean in owned and iban_clean in _MOCK_SALDI:
        return {
            "iban": iban_clean,
            "saldo": _MOCK_SALDI[iban_clean],
            "valuta": "EUR",
        }
    return {"error": result}


@mcp.tool()
async def cerca_policy(query: str) -> list[str]:
    """Cerca documenti policy nel knowledge base usando il motore RAG."""
    try:
        async with SessionLocal() as db:
            svc = RAGService(db=db, user_role="admin")
            response = await svc.ask(query)
        results: list[str] = []
        if response.answer:
            results.append(response.answer)
        if response.citations:
            results.append(f"Documenti consultati: {len(response.citations)}")
        return results if results else ["Nessuna policy trovata per la query."]
    except Exception as exc:
        logger.warning("RAG non disponibile: %s", exc)
        return [f"Servizio RAG non disponibile: {exc}"]


# ── Resources ──────────────────────────────────

@mcp.resource("policy://{nome}")
async def leggi_policy(nome: str) -> str:
    """Restituisce il testo integrale di una policy aziendale per nome."""
    key = nome.strip().lower()
    content = _LOADED_POLICIES.get(key)
    if content is None:
        available = ", ".join(sorted(_LOADED_POLICIES))
        return f"Policy '{nome}' non trovata. Disponibili: {available}"
    return content


# ── Prompts ────────────────────────────────────

@mcp.prompt()
def classifica_transazione_prompt(importo: float, descr: str) -> str:
    """Costruisce un prompt strutturato per classificare una transazione."""
    return (
        f"Classifica la seguente transazione finanziaria:\n\n"
        f"Importo: EUR {importo:,.2f}\n"
        f"Descrizione: {descr}\n\n"
        f"Indica:\n"
        f"1. Livello di rischio (basso / medio / alto)\n"
        f"2. Motivazione sintetica\n"
        f"3. Eventuali verifiche AML/KYC necessarie"
    )


# ── Entrypoint ──────────────────────────────────

sse_app = mcp.sse_app()


# ── FastAPI wrapper ─────────────────────────────

from fastapi import FastAPI
from starlette.responses import HTMLResponse

app = FastAPI(title="FinAssist MCP Server")


@app.get("/")
async def root():
    return HTMLResponse(
        "<h1>FinAssist MCP Server</h1>"
        "<p>Server MCP attivo su porta 8001.</p>"
        "<h2>Endpoints</h2>"
        "<ul>"
        '<li><a href="/health">/health</a> — Health check</li>'
        '<li><a href="/sse">/sse</a> — SSE (MCP client)</li>'
        '<li><a href="/tools">/tools</a> — Elenco tool</li>'
        "</ul>"
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "server": "FinAssist MCP",
        "tools": ["get_saldo", "cerca_policy"],
        "resources": ["policy://{nome}"],
        "prompts": ["classifica_transazione_prompt"],
    }


@app.get("/tools")
async def list_tools():
    from mcp.server.fastmcp import FastMCP
    tools = await mcp.list_tools()
    return {
        "tools": [
            {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
            for t in tools
        ]
    }


app.mount("/", sse_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mcp_server.finassist_mcp:app", host="0.0.0.0", port=8001)
