"""Router per gli endpoint /transactions."""

from fastapi import APIRouter, status, Depends
from app.services.scoring_service import ScoringService
from app.dependencies import get_scoring_service

from app.schemas.transactions import (
    BatchScoreRequest,
    BatchScoreResponse,
    TransactionRequest,
    TransactionScored,
    TransactionIn,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])
router_new = APIRouter(prefix="/api/v1", tags=["transactions"])

recent_transactions: list[TransactionScored] = []


@router.post(
    "/score_new",
    response_model=TransactionScored,
    status_code=status.HTTP_200_OK,
    summary="classifica una transazione",
)
async def score_transaction(payload: TransactionIn, service:ScoringService = Depends(get_scoring_service)) -> TransactionScored:
    """Classifica una singola transazione."""
    result = await service.score(payload)

    recent_transactions.append(result)

    return result


@router.post(
    "/score/batch",
    response_model=list[TransactionScored],
    status_code=status.HTTP_200_OK,
    summary="classifica batch di transazioni",
)
async def score_batch(payload: list[TransactionIn], service: ScoringService = Depends(get_scoring_service)) -> list[TransactionScored]:
    """Classifica una singola transazione."""
    result = await service.post_score_batch(payload)

    recent_transactions.extend(result)

    return result


@router.get(
    "/recent",
    response_model=list[TransactionScored],
    status_code=status.HTTP_200_OK,
    summary="ritorna le ultime 20 transazioni",
)
async def get_recent_trx() -> list[TransactionScored]:

    return recent_transactions[-20:]


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    tags=["health"],
)
async def health_live() -> dict[str, str]:
    return {"status": "live"}


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    tags=["health"],
)
async def health_ready() -> dict[str, str]:
    return {"status": "ready"}


@router.post("/score", response_model=TransactionScored, status_code=status.HTTP_200_OK)
async def score_transaction(payload: TransactionRequest) -> TransactionScored:
    """Classifica una singola transazione."""
    # implementazione vera nel Code Blueprint, qui mock
    return TransactionScored(
        transazione=payload,
        score=42,
        fascia="MEDIUM",
    )


@router.post("/batch-score", response_model=BatchScoreResponse)
async def batch_score(payload: BatchScoreRequest) -> BatchScoreResponse:
    """Classifica un batch di transazioni in parallelo."""
    return BatchScoreResponse(
        totale_input=len(payload.transazioni),
        totale_classificate=0,
        classificate=[],
        errori=[],
    )
