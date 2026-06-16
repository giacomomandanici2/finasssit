from __future__ import annotations

import os
from datetime import datetime

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
        response = await self._client.embeddings.create(
            model="text-embedding-3-small",
            input=[query],
        )
        embedding = response.data[0].embedding

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
        return [
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
