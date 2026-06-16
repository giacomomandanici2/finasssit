from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text

from app.kb.models import KBChunk
from app.kb.service import KBSearchService


@pytest.fixture(autouse=True)
async def enable_vector(async_engine):
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


@pytest.mark.asyncio
async def test_search_orders_by_distance(db_session):
    vec_a = [0.01] * 1536
    vec_b = [0.50] * 1536
    vec_c = [0.99] * 1536

    db_session.add_all([
        KBChunk(document_id="doc1", section="sez1", content="aaa basso",
                embedding=vec_a, access_role="public", language="it"),
        KBChunk(document_id="doc2", section="sez2", content="bbb medio",
                embedding=vec_b, access_role="public", language="it"),
        KBChunk(document_id="doc3", section="sez3", content="ccc alto",
                embedding=vec_c, access_role="public", language="it"),
    ])
    await db_session.commit()

    fake_embedding = [0.0] * 1536
    mock_response = AsyncMock()
    mock_response.data = [AsyncMock(embedding=fake_embedding)]
    mock_create = AsyncMock(return_value=mock_response)

    service = KBSearchService(db_session, openai_api_key="sk-test")
    with patch.object(service._client.embeddings, "create", mock_create):
        results = await service.search(query="test query", roles=["public"], k=3)

    assert len(results) == 3
    assert results[0].score <= results[1].score <= results[2].score
    assert results[0].document_id == "doc1"
    assert results[1].document_id == "doc2"
    assert results[2].document_id == "doc3"


@pytest.mark.asyncio
async def test_search_filters_by_role(db_session):
    vec = [0.10] * 1536

    db_session.add_all([
        KBChunk(document_id="pub", section="s", content="publico",
                embedding=vec, access_role="public", language="it"),
        KBChunk(document_id="comp", section="s", content="solo compliance",
                embedding=vec, access_role="compliance_only", language="it"),
    ])
    await db_session.commit()

    mock_response = AsyncMock()
    mock_response.data = [AsyncMock(embedding=vec)]
    mock_create = AsyncMock(return_value=mock_response)

    service = KBSearchService(db_session, openai_api_key="sk-test")
    with patch.object(service._client.embeddings, "create", mock_create):
        results = await service.search(query="x", roles=["public"], k=10)

    assert len(results) == 1
    assert results[0].document_id == "pub"
