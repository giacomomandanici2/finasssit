"""Router per gli endpoint API v1 di FinAssist AI."""

from fastapi import APIRouter, Depends, status

from app.dependencies import get_scoring_service
from app.schemas.transactions import (
    TransactionIn,
    TransactionScored,
)
from app.services.scoring_service import ScoringService

router = APIRouter(
    prefix="/api/v1",
    tags=["transactions"],
)

recent_transactions: list[TransactionScored] = []


@router.post(
    "/score",
    response_model=TransactionScored,
    status_code=status.HTTP_200_OK,
    summary="Classifica una singola transazione",
)
async def score_transaction(
    payload: TransactionIn,
    service: ScoringService = Depends(get_scoring_service),
) -> TransactionScored:
    """Classifica una singola transazione."""

    result = await service.post_score(payload)

    recent_transactions.append(result)

    return result


@router.post(
    "/score/batch",
    response_model=list[TransactionScored],
    status_code=status.HTTP_200_OK,
    summary="Classifica un batch di transazioni",
)
async def score_batch(
    payload: list[TransactionIn],
    service: ScoringService = Depends(get_scoring_service),
) -> list[TransactionScored]:
    """Classifica più transazioni in parallelo."""

    result = await service.score_batch(payload)

    recent_transactions.extend(result)

    return result


@router.get(
    "/recent",
    response_model=list[TransactionScored],
    status_code=status.HTTP_200_OK,
    summary="Ritorna le ultime 20 transazioni",
)
async def get_recent_transactions() -> list[TransactionScored]:
    """Restituisce le ultime 20 transazioni elaborate."""

    return recent_transactions[-20:]


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Liveness probe",
)
async def health_live() -> dict[str, str]:
    """Verifica che il servizio sia attivo."""

    return {"status": "live"}


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Readiness probe",
)
async def health_ready() -> dict[str, str]:
    """Verifica che il servizio sia pronto a ricevere traffico."""

    return {"status": "ready"}