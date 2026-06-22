"""MCP Client demo — lista tool, chiama get_saldo."""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone, timedelta

import jwt
from mcp import ClientSession
from mcp.client.sse import sse_client

from app.core.config import settings

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
USER_ID = int(os.getenv("MCP_DEMO_USER", "1"))
IBAN = os.getenv("MCP_DEMO_IBAN", "IT60X0542811101000000123456")
SEP = "=" * 50


def _make_token() -> str:
    users = {1: "admin", 2: "retail_user"}
    payload = {
        "sub": str(USER_ID),
        "role": users.get(USER_ID, "admin"),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)


async def main() -> None:
    token = _make_token()
    headers = {"Authorization": f"Bearer {token}"}

    print(f"[connect] Connessione a {MCP_SERVER_URL}/sse ...")
    print(f"[user]   Utente: {USER_ID}")

    async with sse_client(
        url=f"{MCP_SERVER_URL}/sse",
        headers=headers,
    ) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("[ok]     Connesso!\n")

            # ── 1. Lista tool ──────────────────────────
            print(SEP)
            print("[tools]  TOOL DISPONIBILI")
            print(SEP)
            tools = await session.list_tools()
            for t in tools.tools:
                print(f"  [-] {t.name}")
                print(f"     {t.description}")
                if t.inputSchema and "properties" in t.inputSchema:
                    for param, meta in t.inputSchema["properties"].items():
                        print(f"     +- {param}: {meta.get('type', 'any')}")
                print()

            # ── 2. Chiama get_saldo ────────────────────
            print(SEP)
            print(f'[call]   CHIAMATA get_saldo(iban="{IBAN}")')
            print(SEP)
            result = await session.call_tool("get_saldo", arguments={"iban": IBAN})
            for content in result.content:
                if content.type == "text":
                    try:
                        data = json.loads(content.text)
                        print(f"   IBAN:   {data.get('iban', '?')}")
                        print(f"   Saldo:  EUR {data.get('saldo', 0):,.2f}")
                        print(f"   Valuta: {data.get('valuta', '?')}")
                    except (json.JSONDecodeError, TypeError):
                        print(f"   Risultato: {content.text}")
                else:
                    print(f"   [{content.type}] {content.text}")

            # ── 3. Chiama get_saldo con IBAN errato ───
            print()
            print(SEP)
            print("[fail]   CHIAMATA get_saldo (IBAN non tuo)")
            print(SEP)
            result = await session.call_tool(
                "get_saldo", arguments={"iban": "IT60X0542811101000000123458"}
            )
            for content in result.content:
                if content.type == "text":
                    print(f"   Risultato: {content.text}")

            print()
            print("[done]   Demo completata.")


if __name__ == "__main__":
    asyncio.run(main())
