"""Audit log MCP — chi ha chiamato cosa quando."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from mcp_server.auth import MCPUser

logger = logging.getLogger("mcp.audit")


def log_tool_call(
    user: MCPUser,
    tool_name: str,
    params: dict,
    result: object = None,
    error: str | None = None,
) -> None:
    """Registra una chiamata tool nel log strutturato."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "tool_call",
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "tool": tool_name,
        "params": _sanitize(params),
        "error": error,
    }
    if result is not None:
        entry["result_summary"] = _summarize(result)

    logger.info("AUDIT %s", json.dumps(entry, default=str))


def log_auth_result(
    user: MCPUser | None,
    success: bool,
    reason: str | None = None,
) -> None:
    """Registra un tentativo di autenticazione."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "auth",
        "success": success,
        "user_id": user.id if user else None,
        "username": user.username if user else None,
        "role": user.role if user else None,
        "reason": reason,
    }
    logger.info("AUDIT %s", json.dumps(entry, default=str))


def log_rate_limit(
    user: MCPUser,
    remaining: int,
    max_steps: int,
) -> None:
    """Registra un evento di rate limiting."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "rate_limit",
        "user_id": user.id,
        "username": user.username,
        "remaining": remaining,
        "max_steps": max_steps,
    }
    logger.info("AUDIT %s", json.dumps(entry, default=str))


def _sanitize(params: dict) -> dict:
    """Rimuove dati sensibili (IBAN parziale) dai log."""
    safe = {}
    for k, v in params.items():
        if k in ("iban", "iban_sorgente", "iban_destinazione") and isinstance(v, str):
            safe[k] = v[:8] + "****" if len(v) > 8 else v
        else:
            safe[k] = v
    return safe


def _summarize(result: object) -> str:
    if isinstance(result, dict):
        return json.dumps({k: v for k, v in result.items() if k != "error"}, default=str)[:200]
    if isinstance(result, (list, tuple)):
        return f"[{len(result)} items]"
    return str(result)[:200]
