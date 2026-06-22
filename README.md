# FinAssist AI

## Secrets & Credenziali

I valori sensibili (`jwt_secret`, `azure_openai_key`, `api_token`) usano `pydantic.SecretStr`.
In sviluppo si caricano da file `.env` (già in `.gitignore`).

### In produzione

Mai committare secrets. Usare un vault esterno:

- **Azure Key Vault** — caricare i segreti e referenziarli via env vars iniettate dal cluster (AKS + Secrets Store CSI Driver)
- **AWS Secrets Manager / Parameter Store** — stessa logica via env vars
- **Docker Secrets** — mountare `/run/secrets/*` e settare `FILE env var` (es. `JWT_SECRET_FILE`)

Le env var di configurazione sono:

| Variabile | Tipo | Sensibile |
|-----------|------|-----------|
| `DATABASE_URL` | `str` | Sì |
| `JWT_SECRET` | `SecretStr` | Sì |
| `AZURE_OPENAI_KEY` | `SecretStr` | Sì |
| `API_TOKEN` | `SecretStr` | Sì |
| `AZURE_OPENAI_ENDPOINT` | `str` | No |
| `REDIS_URL` | `str` | No |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `str` | No |

I campi `SecretStr` vengono mascherati in log e serializzazione.
