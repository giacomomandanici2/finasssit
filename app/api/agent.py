import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.triage import build_triage_agent
from app.agents.tracing import (
    TracingHooks,
    multi_agent_run_span,
    get_tracer,
)
from app.auth.deps import CurrentUser
from app.core.db import SessionDep
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.repositories.messages import MessagesRepository


_tracer = get_tracer()

_SPECIALIST_NAMES = {"operations_agent", "compliance_agent", "rating_agent"}


class AgentAskRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: int | None = None


class AgentAskResponse(BaseModel):
    answer: str
    specialist_used: str | None = None
    steps_total: int
    citations: list[str] = []


router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/ask", response_model=AgentAskResponse)
async def agent_ask(
    body: AgentAskRequest,
    db: SessionDep,
    current_user: CurrentUser,
) -> AgentAskResponse:
    if body.session_id is not None:
        session = await db.get(ChatSession, body.session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {body.session_id} not found",
            )
    else:
        session = ChatSession(user_id=str(current_user.id))
        db.add(session)
        await db.flush()

    hooks = TracingHooks(_tracer)
    agent = build_triage_agent(user=current_user, db=db, hooks=hooks)

    with multi_agent_run_span(
        tracer=_tracer,
        user_id=str(current_user.id),
        query=body.query,
    ):
        result = await agent.a_run(body.query)

    repo = MessagesRepository(db)
    await repo.create(
        Message(session_id=session.id, role="user", content=body.query)
    )
    await repo.create(
        Message(
            session_id=session.id,
            role="assistant",
            content=result.text or "",
        )
    )

    specialist_used = None
    for block in result.tools_used:
        if block.name in _SPECIALIST_NAMES:
            specialist_used = block.name
            break

    answer_text = result.text or ""
    citations = sorted(
        set(
            m for m in re.findall(r"\[(\d+)\]", answer_text)
        )
    )

    return AgentAskResponse(
        answer=answer_text,
        specialist_used=specialist_used,
        steps_total=result.index + 1,
        citations=citations,
    )
