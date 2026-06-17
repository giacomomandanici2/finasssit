from __future__ import annotations

import logging
import re

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import LLMClient, get_llm
from app.rag.kb_retriever import KBRetriever
from app.rag.prompt_builder import PromptBuilder
from app.rag.query_rewriter import QueryRewriter
from app.rag.schemas import RAGResponse

logger = logging.getLogger(__name__)


class _RAGAnswer(BaseModel):
    answer: str


class RAGService:
    def __init__(
        self,
        db: AsyncSession,
        user_role: str = "retail",
        llm: LLMClient | None = None,
    ) -> None:
        self._db = db
        self._user_role = user_role
        self._llm = llm or get_llm()
        self._rewriter = QueryRewriter(self._llm)
        self._retriever = KBRetriever(db, user_role)
        self._builder = PromptBuilder()
        self.last_chunks: list[dict] = []

    async def ask(self, query: str, k: int = 5) -> RAGResponse:
        query = query.strip()
        if not query:
            return RAGResponse(answer="", citations=[])

        # 1 — Query rewriting
        search_query = await self._rewriter.rewrite(query, role=self._user_role)

        # 2 — Role-filtered KB retrieval
        chunks = await self._retriever.retrieve(search_query, k=k)
        self.last_chunks = chunks

        if not chunks:
            return RAGResponse(
                answer="Nessun documento rilevante trovato nel knowledge base.",
                citations=[],
            )

        # 3 — Build prompt with [1], [2], … citations
        messages = self._builder.build(query, chunks)

        # 4 — LLM structured generation
        try:
            result = await self._llm.chat(messages, _RAGAnswer)
        except Exception as exc:
            logger.error("RAG LLM call failed: %s", exc)
            return self._fallback(chunks)

        # 5 — Post-validation: every [n] must reference an actual chunk
        answer_text = result.answer
        cited_indices = {
            int(m) for m in re.findall(r"\[(\d+)\]", answer_text)
        }
        num_chunks = len(chunks)
        valid_indices = {i for i in cited_indices if 1 <= i <= num_chunks}

        if cited_indices != valid_indices:
            invalid = cited_indices - valid_indices
            logger.warning(
                "Invalid citations %s — valid range is 1..%d",
                sorted(invalid),
                num_chunks,
            )
            for idx in invalid:
                answer_text = re.sub(rf"\[{idx}\]", "", answer_text)
            answer_text = re.sub(r" +", " ", answer_text).strip()

        return RAGResponse(
            answer=answer_text,
            citations=sorted(valid_indices),
        )

    def _fallback(self, chunks: list[dict]) -> RAGResponse:
        snippet = chunks[0]["content"][:500] if chunks else ""
        return RAGResponse(
            answer=(
                "Non è stato possibile generare una risposta. "
                "Ecco il documento più pertinente trovato:\n\n"
                f"{snippet}"
            ),
            citations=[1] if chunks else [],
        )
