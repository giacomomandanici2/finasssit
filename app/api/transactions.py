from fastapi import APIRouter, HTTPException, status

from app.core.db import SessionDep
from app.repositories.transaction import TransactionsRepository
from app.schemas.transactions import TransazioneResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=list[TransazioneResponse])
async def list_transactions(db: SessionDep, limit: int = 20):
    repo = TransactionsRepository(db)
    txs = await repo.list_recent(limit=limit)
    return txs


@router.get("/{tx_id}", response_model=TransazioneResponse)
async def get_transaction(tx_id: str, db: SessionDep):
    repo = TransactionsRepository(db)
    tx = await repo.get_by_tx_id(tx_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transazione {tx_id} non trovata",
        )
    return tx
