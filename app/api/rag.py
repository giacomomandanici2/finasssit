import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth.deps import CurrentUser
from app.core.db import SessionDep
from app.core.slowrate import limiter
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.repositories.messages import MessagesRepository
from app.rag.schemas import (
    CitationItem,
    RAGAnswerRequest,
    RAGAnswerResponse,
)
from app.rag.service import RAGService

router = APIRouter(
    prefix="/api/v1/rag",
    tags=["rag"],
)


@router.post("/answer", response_model=RAGAnswerResponse)
@limiter.limit("10/minute")
async def rag_answer(
    body: RAGAnswerRequest,
    db: SessionDep,
    current_user: CurrentUser,
) -> RAGAnswerResponse:
    service = RAGService(db=db, user_role=current_user.role)
    result = await service.ask(body.query)

    citations = [
        CitationItem(
            id=service.last_chunks[idx - 1]["id"],
            document=service.last_chunks[idx - 1]["document_id"],
            section=service.last_chunks[idx - 1]["section"],
        )
        for idx in result.citations
    ]

    request_id = str(uuid.uuid4())

    if body.session_id is not None:
        stmt = select(ChatSession).where(ChatSession.id == body.session_id)
        session = await db.scalar(stmt)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        repo = MessagesRepository(db)
        await repo.create(
            Message(
                session_id=body.session_id,
                role="user",
                content=body.query,
            )
        )
        await repo.create(
            Message(
                session_id=body.session_id,
                role="assistant",
                content=result.answer,
            )
        )

    return RAGAnswerResponse(
        answer=result.answer,
        citations=citations,
        request_id=request_id,
    )
