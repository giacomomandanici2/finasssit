"""Smoke test end-to-end per FinAssist AI.

Prerequisito: stack avviato con `docker compose up --build`

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone, timedelta

import jwt
import requests

BASE_URL = "http://localhost:8000"
MCP_URL = "http://localhost:8001"
SEP = "-" * 60
PASS = 0
FAIL = 0


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    print(f"  ✓ {msg}")


def fail(msg: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    print(f"  ✗ {msg}")
    if detail:
        print(f"    └─ {detail}")


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        ok(name)
    else:
        fail(name, detail)


def request(method: str, url: str, **kwargs) -> requests.Response:
    return requests.request(method, url, timeout=15, **kwargs)


def main(base_url: str) -> None:
    global PASS, FAIL
    PASS = FAIL = 0

    token: str | None = None
    compliance_token: str | None = None

    print(SEP)
    print("  SMOKE TEST — FinAssist AI")
    print(f"  Base URL: {base_url}")
    print(SEP)

    # ============================================================
    # 1. Healthcheck
    # ============================================================
    print("\n1. Healthcheck")
    r = request("GET", f"{base_url}/health/live")
    check("GET /health/live → 200", r.status_code == 200, r.text)

    r = request("GET", f"{base_url}/health/ready")
    if r.status_code == 200:
        ok("GET /health/ready → 200")
    elif r.status_code == 503:
        ok("GET /health/ready → 503 (degraded)")
    else:
        fail("GET /health/ready → unexpected", str(r.status_code))

    # ============================================================
    # 2. Auth flow: Register → Login → JWT
    # ============================================================
    print("\n2. Auth flow")
    test_user = f"smoke_{int(time.time())}"
    r = request("POST", f"{base_url}/api/v1/auth/register",
                json={"username": test_user, "password": "test123", "role": "retail"})
    if r.status_code == 201:
        ok(f"POST /auth/register → {r.status_code} (created)")
    elif r.status_code == 409:
        ok(f"POST /auth/register → {r.status_code} (already exists)")
    else:
        fail("POST /auth/register", f"status={r.status_code} body={r.text}")

    r = request("POST", f"{base_url}/api/v1/auth/login",
                json={"username": test_user, "password": "test123"})
    check("POST /auth/login → 200", r.status_code == 200, r.text)
    if r.status_code == 200:
        token = r.json().get("access_token")
        check("JWT token ricevuto", bool(token))

    # Login come admin (pre-seed)
    r = request("POST", f"{base_url}/api/v1/auth/login",
                json={"username": "admin", "password": "admin"})
    check("POST /auth/login (admin) → 200", r.status_code == 200, r.text)
    if r.status_code == 200:
        token = r.json().get("access_token")

    # Login come compliance_user (pre-seed)
    r = request("POST", f"{base_url}/api/v1/auth/login",
                json={"username": "compliance_user", "password": "compliance_lead"})
    check("POST /auth/login (compliance) → 200", r.status_code == 200, r.text)
    if r.status_code == 200:
        compliance_token = r.json().get("access_token")

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    compliance_headers = {"Authorization": f"Bearer {compliance_token}"} if compliance_token else {}

    if not token:
        print("  ⚠ Nessun token JWT — salto test che richiedono auth")
        print(SEP)
        sys.exit(1)

    # ============================================================
    # 3. Transaction scoring
    # ============================================================
    print("\n3. Transaction scoring")
    r = request("POST", f"{base_url}/score",
                headers=headers,
                json={
                    "transaction_id": "SMOKE001",
                    "amount": 1500.00,
                    "currency": "EUR",
                    "counterparty": "SmokeTestCorp",
                    "description": "Smoke test transazione",
                    "type": "wire_transfer",
                })
    check("POST /score → 200/201", r.status_code in (200, 201), r.text)

    r = request("GET", f"{base_url}/api/v1/recent?limit=5", headers=headers)
    check("GET /api/v1/recent → 200", r.status_code == 200, r.text)

    if r.status_code == 200:
        data = r.json()
        check("Transazione compare in recenti",
              any(tx.get("transaction_id") == "SMOKE001" for tx in (data if isinstance(data, list) else [])),
              str(data)[:200])

    # ============================================================
    # 4. RAG / KB
    # ============================================================
    print("\n4. RAG + Knowledge Base")
    r = request("POST", f"{base_url}/api/v1/rag/answer",
                headers=headers,
                json={"query": "cossa serve per aprire un conto", "session_id": None})
    if r.status_code == 200:
        ok("POST /rag/answer → 200")
        data = r.json()
        if data.get("citations"):
            ok(f"Risposta con {len(data['citations'])} citations")
        else:
            ok("Risposta ricevuta (senza citations)")
    else:
        fail("POST /rag/answer", f"status={r.status_code} body={r.text}")

    # ============================================================
    # 5. Agent multi-agente (admin → retail flow)
    # ============================================================
    print("\n5. Agent — saldo (retail)")
    r = request("POST", f"{base_url}/api/v1/agent/ask",
                headers=headers,
                json={"query": "qual è il mio saldo?", "session_id": None})
    if r.status_code == 200:
        ok("POST /agent/ask (saldo) → 200")
        data = r.json()
        check("Risposta contiene answer", bool(data.get("answer")), str(data)[:300])
        check("Risposta contiene specialist_used", bool(data.get("specialist_used")), str(data.get("specialist_used")))
        check("Risposta contiene steps_total", isinstance(data.get("steps_total"), int))
    else:
        fail("POST /agent/ask (saldo)", f"status={r.status_code} body={r.text}")

    # ============================================================
    # 6. Agent compliance_user → compliance_agent
    # ============================================================
    print("\n6. Agent — compliance (MIFID)")
    r = request("POST", f"{base_url}/api/v1/agent/ask",
                headers=compliance_headers,
                json={"query": "cosa dice la MIFID?"})
    if r.status_code == 200:
        ok("POST /agent/ask (MIFID) → 200")
        data = r.json()
        check("Risposta contiene answer", bool(data.get("answer")), str(data)[:300])
        specialist = data.get("specialist_used")
        if specialist:
            ok(f"Specialist usato: {specialist}")
        else:
            ok("Risposta ricevuta (specialist non identificato)")
    else:
        fail("POST /agent/ask (MIFID)", f"status={r.status_code} body={r.text}")

    # ============================================================
    # 7. MCP Server via client demo script
    # ============================================================
    print("\n7. MCP Server")
    mcp_token = jwt.encode(
        {"sub": "1", "role": "admin", "iat": datetime.now(timezone.utc), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "change-me",
        algorithm="HS256",
    )
    r = request("GET", f"{MCP_URL}/tools", headers={"Authorization": f"Bearer {mcp_token}"})
    if r.status_code == 200:
        ok("GET /tools → 200")
    else:
        fail("GET /tools", f"status={r.status_code} body={r.text}")

    r = request("GET", f"{MCP_URL}/health", headers={"Authorization": f"Bearer {mcp_token}"})
    check("GET /health (MCP) → 200", r.status_code == 200, r.text)

    # ============================================================
    # 8. RESULT
    # ============================================================
    print(f"\n{SEP}")
    total = PASS + FAIL
    print(f"  RISULTATO: {PASS}/{total} passed, {FAIL}/{total} failed")
    print(SEP)

    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test FinAssist AI")
    parser.add_argument("--base-url", default=BASE_URL, help="API base URL")
    args = parser.parse_args()
    main(args.base_url)
