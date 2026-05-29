from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.llm import get_llm
from app.core.db import SessionDep
from app.repositories.messages import MessagesRepository
from app.repositories.transaction import TransactionsRepository
from app.schemas.sessions import SessionWithMessagesResponse
from app.schemas.transactions import TransazioneResponse
from app.services.risk_explanation import (
    RiskExplanationService,
    SpiegazioneRischio,
)

LLMDep = Depends(get_llm)

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get(
    "/sessions/{session_id}/messages",
    response_model=SessionWithMessagesResponse,
)
async def get_session_messages(session_id: int, db: SessionDep):
    repo = MessagesRepository(db)
    session = await repo.list_by_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sessione {session_id} non trovata",
        )
    return session


@router.get("/recent", response_model=list[TransazioneResponse])
async def get_recent(db: SessionDep, limit: int = 20):
    repo = TransactionsRepository(db)
    return await repo.list_recent(limit=limit)


@router.post("/explain/{tx_id}", response_model=SpiegazioneRischio)
async def explain_transaction(
    tx_id: str,
    db: SessionDep,
    llm=LLMDep,
):
    repo = TransactionsRepository(db)
    tx = await repo.get_by_tx_id(tx_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transazione {tx_id} non trovata",
        )
    service = RiskExplanationService(llm_client=llm)
    return await service.genera_spiegazione(tx)
