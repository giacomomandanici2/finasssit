"""FinAssist MCP Server — Auth, rate limit, audit log.

Transport: HTTP+SSE su porta 8001.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP, Context

from app.core.db import SessionLocal
from app.agents.tools import make_get_saldo, _MOCK_SALDI, _USER_IBANS
from app.rag.service import RAGService
from mcp_server.auth import get_current_user, MCPUser
from mcp_server import audit

logger = logging.getLogger(__name__)

_LOADED_POLICIES: dict[str, str] = {}

# Rate limit: user_id -> steps rimasti
_RATE_LIMIT_BUDGET: dict[str, int] = {}
_RATE_LIMIT_MAX = 30


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
    global _LOADED_POLICIES, _RATE_LIMIT_BUDGET
    _LOADED_POLICIES = _load_policies()
    _RATE_LIMIT_BUDGET = {}
    logger.info(
        "MCP server FinAssist avviato — %d policy, rate max=%d",
        len(_LOADED_POLICIES),
        _RATE_LIMIT_MAX,
    )
    yield


mcp = FastMCP(
    "FinAssist",
    instructions=(
        "Server MCP per operazioni bancarie e compliance. "
        "Autenticazione: Bearer JWT in ctx.meta['token']."
    ),
    lifespan=lifespan,
)


# ── Helper auth + rate limit ────────────────────

class AuthError(Exception):
    pass


class RateLimitError(Exception):
    pass


async def _authenticate(ctx: Context) -> MCPUser:
    user = await get_current_user(ctx)
    if user is None:
        raise AuthError("Unauthorized — fornisci un Bearer JWT valido in ctx.meta['token']")
    return user


def _check_rate_limit(user: MCPUser) -> int:
    key = f"user:{user.id}"
    remaining = _RATE_LIMIT_BUDGET.get(key, _RATE_LIMIT_MAX)
    if remaining <= 0:
        raise RateLimitError(
            f"Rate limit superato per {user.username} "
            f"({_RATE_LIMIT_MAX} step massimi)"
        )
    _RATE_LIMIT_BUDGET[key] = remaining - 1
    audit.log_rate_limit(user, remaining - 1, _RATE_LIMIT_MAX)
    return remaining - 1


# ── Tools ─────────────────────────────────────

@mcp.tool()
async def get_saldo(iban: str, ctx: Context) -> dict:
    """Ottiene il saldo corrente per un IBAN intestato all'utente autenticato."""
    try:
        user = await _authenticate(ctx)
        _check_rate_limit(user)
    except (AuthError, RateLimitError) as e:
        audit.log_auth_result(None, False, reason=str(e))
        return {"error": str(e)}

    user_key = f"user_{user.id:03d}"
    tool = make_get_saldo(user_key)
    result = await tool(iban=iban)
    owned = _USER_IBANS.get(user_key, [])
    iban_clean = iban.strip().replace(" ", "")
    if iban_clean in owned and iban_clean in _MOCK_SALDI:
        payload = {
            "iban": iban_clean,
            "saldo": _MOCK_SALDI[iban_clean],
            "valuta": "EUR",
        }
        audit.log_tool_call(user, "get_saldo", {"iban": iban_clean}, result=payload)
        return payload
    audit.log_tool_call(user, "get_saldo", {"iban": iban_clean}, error=result)
    return {"error": result}


@mcp.tool()
async def cerca_policy(query: str, ctx: Context) -> list[str]:
    """Cerca documenti policy nel knowledge base usando il motore RAG."""
    try:
        user = await _authenticate(ctx)
        _check_rate_limit(user)
    except (AuthError, RateLimitError) as e:
        audit.log_auth_result(None, False, reason=str(e))
        return [f"Errore: {e}"]

    params = {"query": query}
    try:
        async with SessionLocal() as db:
            svc = RAGService(db=db, user_role=user.role)
            response = await svc.ask(query)
        results: list[str] = []
        if response.answer:
            results.append(response.answer)
        if response.citations:
            results.append(f"Documenti consultati: {len(response.citations)}")
        if not results:
            results = ["Nessuna policy trovata per la query."]
        audit.log_tool_call(user, "cerca_policy", params, result=results)
        return results
    except Exception as exc:
        logger.warning("RAG non disponibile: %s", exc)
        audit.log_tool_call(user, "cerca_policy", params, error=str(exc))
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
from starlette.responses import HTMLResponse, JSONResponse


class AuthASGIMiddleware:
    """ASGI middleware: valida Bearer token su /sse e /messages.

    Usa ASGI scope (non BaseHTTPMiddleware) per non rompere lo streaming SSE.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] in ("/sse", "/messages"):
            headers = dict(scope.get("headers", []))
            raw = headers.get(b"authorization", b"").decode()
            token = raw.removeprefix("Bearer ") if raw.startswith("Bearer ") else raw
            if not token:
                return await _send_401(send, "Authorization header required (Bearer <JWT>)")
            from mcp_server.auth import _decode_and_resolve
            user = _decode_and_resolve(token)
            if user is None:
                return await _send_401(send, "Invalid or expired token")
            audit.log_auth_result(user, True)
        await self.app(scope, receive, send)


async def _send_401(send, detail: str) -> None:
    body = JSONResponse(status_code=401, content={"error": detail}).body
    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


app = FastAPI(title="FinAssist MCP Server")
app.add_middleware(AuthASGIMiddleware)


@app.get("/")
async def root():
    return HTMLResponse(
        "<h1>FinAssist MCP Server</h1>"
        "<p>Server MCP attivo su porta 8001.</p>"
        "<p>Autenticazione: Bearer JWT via Authorization header o ctx.meta['token'].</p>"
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
        "auth": "Bearer JWT",
        "rate_limit_max": _RATE_LIMIT_MAX,
        "rate_limit_active": len(_RATE_LIMIT_BUDGET),
        "tools": ["get_saldo", "cerca_policy"],
        "resources": ["policy://{nome}"],
        "prompts": ["classifica_transazione_prompt"],
    }


@app.get("/tools")
async def list_tools():
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
