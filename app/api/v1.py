from fastapi import APIRouter, HTTPException, status

from app.core.db import SessionDep
from app.repositories.messages import MessagesRepository
from app.repositories.transaction import TransactionsRepository
from app.schemas.sessions import SessionWithMessagesResponse
from app.schemas.transactions import TransazioneResponse

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
