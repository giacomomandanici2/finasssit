# syntax=docker/dockerfile:1
# ============================================================
# STAGE 1 — Builder: build all Python wheels
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY app/ app/
COPY mcp_server/ mcp_server/

# Build wheels for the project and all its dependencies
RUN pip wheel --no-cache-dir --wheel-dir /wheels .


# ============================================================
# STAGE 2 — Runtime: slim image with only runtime deps
# ============================================================
FROM python:3.12-slim AS runtime

# libpq is needed at runtime by psycopg2 / asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built wheels from builder
COPY --from=builder /wheels /wheels

# Install project from wheels (no build deps needed)
RUN pip install --no-cache-dir --no-index --find-links=/wheels finassist-day03

# Copy application source (overrides any installed package copy)
COPY app/ /app/app/
COPY mcp_server/ /app/mcp_server/
COPY gunicorn.conf.py /app/gunicorn.conf.py
WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup --no-create-home appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import http.client; c=http.client.HTTPConnection('localhost',8000); c.request('GET','/health/live'); r=c.getresponse(); exit(0 if r.status==200 else 1)"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
