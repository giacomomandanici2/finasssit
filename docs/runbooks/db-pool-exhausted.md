# Runbook: Database Connection Pool Exhausted

## Sintomo

- API risponde **HTTP 503** su `/health/ready` → `"postgres": "timeout"` o `"too many clients"`
- Log con `"level": "ERROR"` e messaggio `"TimeoutError: QueuePool limit of size X overflow Y reached"`
- Richieste lente o timeout su qualsiasi operazione che coinvolge il DB
- `SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction'` mostra sessioni bloccate

## Diagnosi

1. **Verificare pool size attuale** — controllare `app/core/db.py` → `pool_size=10, max_overflow=20` (30 connessioni massime)
2. **Controllare connessioni attive su PostgreSQL**:

```bash
# Connessioni totali per database
psql -U finassist -d finassist -c "
SELECT count(*) AS total,
       count(*) FILTER (WHERE state = 'active') AS active,
       count(*) FILTER (WHERE state = 'idle') AS idle,
       count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_tx
FROM pg_stat_activity WHERE datname = 'finassist';
"
```

3. **Identificare connessioni long-running**:

```sql
SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity
WHERE datname = 'finassist' AND state = 'active'
ORDER BY duration DESC;
```

4. **Controllare eventuali lock**:

```sql
SELECT blocked.pid AS blocked_pid, blocking.pid AS blocking_pid, blocked.query
FROM pg_catalog.pg_locks blocked
JOIN pg_catalog.pg_locks blocking ON blocked.pid != blocking.pid
WHERE NOT blocked.granted;
```

## Remediation

### Temporanea (subito)

```bash
# Killare connessioni bloccate più vecchie di 5 minuti
psql -U finassist -d finassist -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'finassist'
  AND state = 'idle in transaction'
  AND age(now(), query_start) > interval '5 minutes';
"
```

### A medio termine

1. **Aumentare pool_size in `app/core/db.py`** (se il DB PostgreSQL lo supporta):

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=20,       # da 10
    max_overflow=40,     # da 20
    pool_pre_ping=True,
    pool_recycle=300,    # ridotto a 5 minuti
)
```

2. **Verificare che `pool_pre_ping=True` e `pool_recycle` siano impostati** (già presenti)
3. **Aggiungere timeout esplicito sulle query**:

```python
from sqlalchemy import text
await session.execute(text("SELECT 1").execution_options(timeout=10))
```

### Definitiva

- Assicurarsi che ogni `get_session()` chiami `session.close()` (già garantito dal `async with` in `app/core/db.py`)
- Controllare che non ci siano `async with SessionLocal()` senza commit/rollback (fixture di test)
- Aggiungere PgBouncer come connection pooler tra app e PostgreSQL
- Se il carico è costante, aumentare `max_connections` in `postgresql.conf` (default: 100)

## Escalation

| Soglia | Azione |
|--------|--------|
| Pool >80% per >5 min | Notifica Slack #alerts |
| Pool 100% per >1 min | Page DevOps (PagerDuty) |
| `pg_stat_activity` mostra >10 lock concorrenti | Coinvolgere DBA (amministratore DB) |

## Riferimenti

- `app/core/db.py` — configurazione engine (pool_size, max_overflow, pool_recycle, pool_pre_ping)
- `app/core/lifespan.py` — `engine.dispose()` in shutdown graceful
- `app/core/log_context.py` — log con `request_id` e `user_id` per tracciare l'origine delle connessioni
- Dashboard Grafana: `PostgreSQL > Connection Pool Usage`
- Comando rapido: `docker exec finassist-postgres psql -U finassist -d finassist -c "SELECT count(*) FROM pg_stat_activity;"`
