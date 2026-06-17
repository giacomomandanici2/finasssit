import hashlib
import logging

from pydantic import BaseModel

from app.ai.llm import LLMClient
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

REWRITE_CACHE_TTL = 3600  # 1 hour


class _Rewritten(BaseModel):
    query: str


class QueryRewriter:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm

    async def rewrite(self, query: str, role: str = "retail") -> str:
        query = query.strip()
        if not query or self._llm is None:
            return query

        key = self._cache_key(query, role)

        redis = get_redis()
        if redis is not None:
            cached = await redis.get(key)
            if cached is not None:
                logger.info("Rewrite cache hit: %r", key)
                return str(cached)

        rewritten = await self._call_llm(query)

        if redis is not None:
            await redis.setex(key, REWRITE_CACHE_TTL, rewritten)
            logger.info("Rewrite cached: %r (TTL=%ds)", key, REWRITE_CACHE_TTL)

        return rewritten

    async def _call_llm(self, query: str) -> str:
        assert self._llm is not None
        messages = [
            {
                "role": "system",
                "content": (
                    "Riscrivi la domanda dell'utente in una query di ricerca "
                    "efficace per un knowledge base di normative finanziarie. "
                    "Restituisci un JSON con un campo 'query' contenente solo "
                    "la query riscritta, senza preamboli."
                ),
            },
            {"role": "user", "content": query},
        ]
        try:
            result = await self._llm.chat(messages, _Rewritten)
            rewritten = result.query.strip()
            logger.info("Query rewritten: %r -> %r", query, rewritten)
            return rewritten
        except Exception:
            logger.warning("Query rewrite failed, using original: %s", query)
            return query

    @staticmethod
    def _cache_key(query: str, role: str) -> str:
        raw = f"{query}|{role}"
        h = hashlib.sha256(raw.encode()).hexdigest()
        return f"rewrite:{h}"
