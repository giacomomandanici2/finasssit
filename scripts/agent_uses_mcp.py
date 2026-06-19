"""Demo: operations_agent che consuma tool dal server MCP.

Avvio:
  1. Terminale 1: python -m mcp_server.finassist_mcp
  2. Terminale 2: python scripts/agent_uses_mcp.py
"""

from __future__ import annotations

import asyncio

from app.agents.mcp_client import (
    _make_default_mcp_client,
    build_operations_agent_with_mcp,
)


async def main() -> None:
    # 1 — Connetti al server MCP
    client = _make_default_mcp_client()
    if client is None:
        print("[ERR] MCP server non raggiungibile su http://localhost:8001")
        print("      Avvia: python -m mcp_server.finassist_mcp")
        return

    try:
        await client.connect()

        # 2 — Lista tool MCP disponibili
        print("=== Tool MCP disponibili ===")
        tools = await client.list_tools()
        for t in tools:
            print(f"  - {t['name']}: {t['description']}")

        # 3 — Chiamata diretta a get_saldo via MCP
        print()
        print("=== get_saldo via MCP (diretto) ===")
        result = await client.call_tool("get_saldo", {"iban": "IT60X0542811101000000123456"})
        print(f"  {result}")

        # 4 — Agent che usa MCP come backend
        print()
        print("=== Agent con tool MCP ===")
        agent = build_operations_agent_with_mcp(mcp_client=client)

        result = await agent.a_run(
            "usa lo strumento function per ottenere saldo di IT60X0542811101000000123456"
        )
        print(f"  Risposta agent: {result.text}")

    finally:
        await client.disconnect()

    print()
    print("[done] Demo completata.")


if __name__ == "__main__":
    asyncio.run(main())
