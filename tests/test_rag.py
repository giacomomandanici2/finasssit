from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from app.models.kb_chunk import KbChunk as KBChunk
from app.rag.kb_retriever import KBRetriever
from app.rag.service import RAGService


@pytest.fixture(autouse=True)
async def enable_vector(async_engine):
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


@pytest.mark.asyncio
async def test_retail_user_does_not_see_compliance_chunks(db_session):
    vec = [0.10] * 1536

    db_session.add_all([
        KBChunk(
            document_id="doc-pub",
            section="s",
            content="contenuto pubblico",
            embedding=vec,
            access_role="public",
            language="it",
        ),
        KBChunk(
            document_id="doc-comp",
            section="s",
            content="solo compliance",
            embedding=vec,
            access_role="compliance_only",
            language="it",
        ),
    ])
    await db_session.commit()

    mock_response = AsyncMock()
    mock_response.data = [AsyncMock(embedding=vec)]
    mock_create = AsyncMock(return_value=mock_response)

    retriever = KBRetriever(db_session, user_role="retail")
    with patch.object(
        retriever._search_service._client.embeddings, "create", mock_create
    ):
        results = await retriever.retrieve(query="test", k=10)

    assert len(results) == 1
    assert results[0]["document_id"] == "doc-pub"


@pytest.mark.asyncio
async def test_empty_retrieval_returns_not_found_without_llm_call(db_session):
    mock_llm = AsyncMock()

    service = RAGService(db=db_session, user_role="retail", llm=mock_llm)

    with (
        patch.object(service._rewriter, "rewrite", AsyncMock(return_value="query")),
        patch.object(service._retriever, "retrieve", AsyncMock(return_value=[])),
    ):
        result = await service.ask("query")

    assert result.answer == "Nessun documento rilevante trovato nel knowledge base."
    assert result.citations == []
    mock_llm.chat.assert_not_called()
