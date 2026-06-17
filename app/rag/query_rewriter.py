import logging

from pydantic import BaseModel

from app.ai.llm import LLMClient

logger = logging.getLogger(__name__)


class _Rewritten(BaseModel):
    query: str


class QueryRewriter:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm

    async def rewrite(self, query: str) -> str:
        query = query.strip()
        if not query or self._llm is None:
            return query

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
