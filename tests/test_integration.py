import pytest
from httpx import AsyncClient

from app.models.scored_transactions import ScoredTransaction
from app.repositories.transaction import TransactionsRepository


@pytest.mark.asyncio
async def test_insert_and_fetch_recent(client: AsyncClient, db_session):
    repo = TransactionsRepository(db_session)

    tx = ScoredTransaction(
        tx_id="test-001",
        iban="IT60X0542811101000000123456",
        importo=15000.0,
        rischio="alto",
        motivazione="Test inserimento",
    )
    await repo.upsert(tx)

    response = await client.get("/api/v1/recent?limit=20")
    assert response.status_code == 200
    data = response.json()

    ids = [item["tx_id"] for item in data]
    assert "test-001" in ids

    match = next(item for item in data if item["tx_id"] == "test-001")
    assert match["importo"] == 15000.0
    assert match["rischio"] == "alto"
    assert match["iban"] == "IT60X0542811101000000123456"
    assert match["motivazione"] == "Test inserimento"
