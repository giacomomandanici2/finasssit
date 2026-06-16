from __future__ import annotations

import logging
import os
import time
from datetime import datetime

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class KBChunkResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: str
    section: str
    content: str
    access_role: str
    language: str
    score: float
    created_at: datetime


class KBSearchService:
    def __init__(
        self,
        db: AsyncSession,
        openai_api_key: str | None = None,
    ) -> None:
        self.db = db
        self._client = AsyncOpenAI(
            api_key=openai_api_key or os.environ.get("OPENAI_API_KEY", ""),
        )

    async def search(
        self,
        query: str,
        roles: list[str],
        k: int = 10,
    ) -> list[KBChunkResult]:
        start = time.monotonic()

        response = await self._client.embeddings.create(
            model="text-embedding-3-small",
            input=[query],
        )
        embedding = response.data[0].embedding

        count_sql = text("SELECT COUNT(*) FROM kb_chunks WHERE access_role = ANY(:roles)")
        total = await self.db.scalar(count_sql, {"roles": roles}) or 0

        sql = text("""
            SELECT
                id, document_id, section, content,
                access_role, language, created_at,
                embedding <=> :q AS distance
            FROM kb_chunks
            WHERE access_role = ANY(:roles)
            ORDER BY distance
            LIMIT :k
        """)

        rows = await self.db.execute(sql, {"q": embedding, "roles": roles, "k": k})
        results = [
            KBChunkResult(
                id=r.id,
                document_id=r.document_id,
                section=r.section,
                content=r.content,
                access_role=r.access_role,
                language=r.language,
                score=float(r.distance),
                created_at=r.created_at,
            )
            for r in rows
        ]

        latency_ms = (time.monotonic() - start) * 1000
        avg_distance = sum(r.score for r in results) / len(results) if results else 0.0

        logger.info(
            "KB search | k=%d latency_ms=%.1f avg_distance=%.4f total_for_roles=%d",
            k,
            latency_ms,
            avg_distance,
            total,
        )

        return results
