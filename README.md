# FinAssist AI

Piattaforma multi-agente per l'analisi finanziaria con agenti specializzati (Operations, Compliance, Rating), server MCP su SSE, e stack DevOps completo (Docker, Nginx, OTel, CI/CD).

## Avvio rapido

```bash
# Clona e configura
cp .env.example .env

# Avvia tutto lo stack
docker compose up --build

# Solo servizi essenziali
docker compose up --build postgres redis api

# Con tracing (Jaeger)
docker compose --profile tracing up --build
```

Servizi esposti:

| Porta | Servizio | URL |
|-------|----------|-----|
| `80` | Nginx (reverse proxy HTTPS) | `https://localhost` |
| `8000` | API (FastAPI — diretto) | `http://localhost:8000` |
| `8001` | MCP Server (SSE) | `http://localhost:8001` |
| `16686` | Jaeger UI (solo con `--profile tracing`) | `http://localhost:16686` |

## Endpoint API

| Metodo | Path | Auth | Descrizione |
|--------|------|------|-------------|
| `POST` | `/api/v1/auth/register` | No | Registra utente |
| `POST` | `/api/v1/auth/login` | No | Login, restituisce JWT |
| `GET` | `/api/v1/recent` | JWT | Transazioni recenti |
| `GET` | `/api/v1/sessions/{id}/messages` | JWT | Messaggi di una sessione |
| `POST` | `/api/v1/explain/{tx_id}` | JWT | Spiegazione AI di una transazione |
| `POST` | `/api/v1/rag/answer` | JWT | RAG: risposta con knowledge base |
| `POST` | `/api/v1/agent/ask` | JWT | Agente multi-agente orchestrato |
| `GET` | `/health/live` | No | Liveness probe |
| `GET` | `/health/ready` | No | Readiness probe (DB + Redis + Azure) |
| `GET` | `/mcp/sse` | JWT | SSE stream per MCP |
| `POST` | `/mcp/messages/` | JWT | Messaggi JSON-RPC MCP |

## Autenticazione JWT

1. **Registrazione**: `POST /api/v1/auth/register` con `{"username": "...", "password": "...", "role": "admin|retail|compliance"}`
2. **Login**: `POST /api/v1/auth/login` restituisce `{"access_token": "<JWT>", "token_type": "bearer"}`
3. **Usa il token**: tutte le route protette richiedono header `Authorization: Bearer <JWT>`

Il JWT contiene:
```json
{
  "sub": "1",
  "role": "admin",
  "iat": 1700000000,
  "exp": 1700003600
}
```
Payload firmato con `JWT_SECRET` (HS256). La validazione avviene senza query al DB in `app/core/slowrate.py` e `app/core/log_context.py` (solo decodifica). La risoluzione utente reale è in `app/auth/deps.py`.

Utenti pre-seed: `admin`/`admin`, `retail_user`/`retail`, `compliance_user`/`compliance_lead`.

## MCP Server

Il server MCP (`mcp_server/finassist_mcp.py`) espone:

- **Tool**: `get_saldo(iban)` — saldo contabile (solo IBAN dell'utente autenticato)
- **Tool**: `cerca_policy(query)` — documenti normativi dalla knowledge base
- **Resource**: `policy://{nome}` — policy aziendale specifica
- **Prompt**: `classifica_transazione` — template per classificazione AML

### Connessione con MCP Inspector

```bash
# Genera un token JWT (esempio con Python)
python -c "
import jwt, time
t = jwt.encode({'sub':'1','role':'admin','iat':time.time(),'exp':time.time()+7200}, 'change-me-in-production')
print(t)
"

# Lancia Inspector
npx @modelcontextprotocol/inspector \
  --transport sse \
  --server-url http://localhost:8001 \
  --header "Authorization: Bearer <TOKEN>"
```

### Demo client

```bash
python scripts/mcp_client_demo.py
```

## Variabili d'ambiente

Tutte le variabili sono documentate in [`.env.example`](.env.example). Copiare in `.env` per sviluppo:

| Variabile | Default | Obbligatoria | Descrizione |
|-----------|---------|--------------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://finassist:finassist_dev_password@localhost:5433/finassist` | Sì | Connessione PostgreSQL |
| `REDIS_URL` | `redis://localhost:6379/0` | No | Cache e idempotency |
| `JWT_SECRET` | `change-me-in-production` | Sì | Chiave firma JWT |
| `JWT_ALGORITHM` | `HS256` | No | Algoritmo JWT |
| `JWT_EXPIRE_MINUTES` | `60` | No | TTL token |
| `AZURE_OPENAI_ENDPOINT` | — | No | Endpoint Azure OpenAI |
| `AZURE_OPENAI_KEY` | — | No | API key (se vuoto → MockClient) |
| `AZURE_OPENAI_DEPLOYMENT` | — | No | Nome deployment |
| `AZURE_OPENAI_API_VERSION` | `2024-10-21` | No | Versione API |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | No | Endpoint OTLP (Jaeger) |

## Secrets

I valori `JWT_SECRET`, `AZURE_OPENAI_KEY` e `API_TOKEN` usano `pydantic.SecretStr`:
- `repr()` e `str()` mostrano `'**********'`
- Accesso reale solo con `.get_secret_value()`
- In produzione usare Azure Key Vault, AWS Secrets Manager o Docker Secrets (vedi [docs/runbooks](docs/runbooks/))

## Composizione servizi

```
nginx:1.27 (TLS + rate limit per IP)
  ├── api (gunicorn + uvicorn workers) → postgres:16 + redis:7
  └── mcp (uvicorn SSE) → postgres:16 + redis:7
```

## Struttura progetto

```
app/
  agents/        Agenti specializzati + triage + tracing + MCP client
  api/           Router FastAPI (v1, agent, rag, kb, auth)
  auth/          Registrazione/login JWT
  core/          DB, config, Redis, rate limiting, logging, OTel
  models/        SQLAlchemy models
  rag/           Retrieval-Augmented Generation
mcp_server/      Server MCP (auth, audit, rate limit, tools, resources, prompts)
scripts/         Demo e utilità (seed users, MCP client, ingest KB)
docs/runbooks/   Runbook operativi
tests/           8 file di test (pytest + testcontainers)
.github/workflows/  CI (ruff → mypy → pytest → bandit → docker build)
```

## Test

```bash
pip install -e ".[dev]"
pytest -v --timeout=180
```

## CI/CD

`.github/workflows/ci.yml`: lint (ruff) → typecheck (mypy) → test (pytest + testcontainers PostgreSQL) → security (bandit + gitleaks) → build Docker image.
