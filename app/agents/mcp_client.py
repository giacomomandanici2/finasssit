"""MCP Client — wrapper che permette agli agent di consumare tool MCP via SSE."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client

from app.agents.tools import safe_tool

logger = logging.getLogger(__name__)


class MCPToolClient:
    """Client MCP che si connette via SSE e chiama tool del server.

    Crea una connessione SSE all'inizializzazione e la riusa per
    chiamate multiple.
    """

    def __init__(self, server_url: str, headers: dict[str, str] | None = None):
        self._server_url = server_url.rstrip("/") + "/sse"
        self._headers = headers or {}
        self._session: ClientSession | None = None
        self._sse_ctx = None

    async def connect(self) -> None:
        """Apre connessione SSE e inizializza la sessione MCP."""
        self._sse_ctx = sse_client(url=self._server_url, headers=self._headers)
        read, write = await self._sse_ctx.__aenter__()
        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()

    async def disconnect(self) -> None:
        """Chiude la sessione MCP e la connessione SSE."""
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None
        if self._sse_ctx:
            await self._sse_ctx.__aexit__(None, None, None)
            self._sse_ctx = None

    async def __aenter__(self) -> MCPToolClient:
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        await self.disconnect()

    async def list_tools(self) -> list[dict]:
        if self._session is None:
            await self.connect()
        assert self._session is not None
        tools = await self._session.list_tools()
        return [
            {"name": t.name, "description": t.description}
            for t in tools.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if self._session is None:
            await self.connect()
        assert self._session is not None
        result = await self._session.call_tool(name, arguments=arguments)
        texts = [
            c.text for c in result.content
            if hasattr(c, "text") and c.type == "text"
        ]
        if texts:
            return texts[0]
        return str(result)


def make_mcp_tool(
    mcp_client: MCPToolClient,
    tool_name: str,
    description: str,
) -> Callable:
    """Crea una funzione tool @safe_tool che chiama un tool MCP remoto."""
    from datapizza.tools import tool

    @tool
    @safe_tool
    async def mcp_wrapper(**kwargs: Any) -> str:
        result = await mcp_client.call_tool(tool_name, kwargs)
        return str(result)

    mcp_wrapper.__name__ = tool_name
    mcp_wrapper.__qualname__ = tool_name
    mcp_wrapper.__doc__ = description
    return mcp_wrapper


def build_operations_agent_with_mcp(
    mcp_client: MCPToolClient | None = None,
    **kwargs: Any,
) -> Any:
    """Costruisce operations_agent che usa tool MCP invece di chiamate dirette."""
    from datapizza.agents import Agent
    from datapizza.clients.factory import ClientFactory, Provider

    if mcp_client is None:
        mcp_client = _make_default_mcp_client()
    if mcp_client is None:
        raise RuntimeError("MCP server non raggiungibile")

    tools = [
        make_mcp_tool(
            mcp_client,
            "get_saldo",
            "Ottiene il saldo corrente per un IBAN intestato all'utente autenticato.",
        ),
    ]

    client = kwargs.pop("client", None) or ClientFactory.create(
        provider=Provider.MOCK, api_key="", model="mock"
    )

    return Agent(
        name="operations_agent_mcp",
        client=client,
        description="Operazioni bancarie via MCP: saldo.",
        system_prompt=(
            "Sei l'agente Operazioni Bancarie (via MCP).\n"
            "Rispondi sempre in italiano.\n"
            "Usa get_saldo per verificare il saldo di un IBAN."
        ),
        tools=tools,
        max_steps=4,
        hooks=kwargs.get("hooks"),
    )


def _make_default_mcp_client() -> MCPToolClient | None:
    import os
    from datetime import datetime, timezone, timedelta

    import jwt

    from app.core.config import settings

    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
    try:
        token = jwt.encode(
            {
                "sub": "1",
                "role": "admin",
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )
        return MCPToolClient(
            server_url=mcp_url,
            headers={"Authorization": f"Bearer {token}"},
        )
    except Exception as exc:
        logger.warning("Impossibile creare default MCP client: %s", exc)
        return None
