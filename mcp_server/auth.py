"""Autenticazione MCP — Bearer token JWT da context, stessa logica di get_current_user."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import jwt
from mcp.server.fastmcp import Context

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MCPUser:
    id: int
    username: str
    role: str


async def get_current_user(ctx: Context) -> MCPUser | None:
    """Risolve l'utente autenticato dal context MCP.

    Cerca il token JWT in ordine:
    1. ctx.request_context.request.headers (Authorization header HTTP)
    2. ctx.request_context.meta (metadati JSON-RPC)
    3. ctx.fastmcp (fallback)
    4. Variabile ambiente MCP_AUTH_TOKEN (solo demo)
    """
    token: str | None = None

    # 1 — HTTP Authorization header via request_context
    rc = ctx.request_context
    if rc and rc.request:
        auth_header = rc.request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    # 2 — JSON-RPC meta
    if not token and rc and rc.meta:
        token = rc.meta.get("token") or rc.meta.get("authorization")

    # 3 — Env fallback (solo demo)
    if not token:
        token = os.getenv("MCP_AUTH_TOKEN")

    if not token:
        return None

    if token.startswith("Bearer "):
        token = token[7:]

    return _decode_and_resolve(token)


def _decode_and_resolve(token: str) -> MCPUser | None:
    """Decodifica JWT e restituisce MCPUser."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Token JWT scaduto")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning("Token JWT non valido: %s", exc)
        return None

    user_id = int(payload["sub"])
    role = payload.get("role", "unknown")

    # Mappa utenti noti (stessa logica di app/auth/deps.py ma senza DB)
    known = {
        1: "admin",
        2: "retail_user",
        3: "compliance_user",
    }
    username = known.get(user_id, f"user_{user_id}")

    return MCPUser(id=user_id, username=username, role=role)
