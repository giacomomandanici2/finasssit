from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.factory import build_agent
from app.agents.tracing import TracingHooks, agent_run_span, get_tracer
from app.auth.deps import CurrentUser
from app.core.db import SessionDep
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.repositories.messages import MessagesRepository


_tracer = get_tracer()


class AgentAskRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: int | None = None


class AgentAskResponse(BaseModel):
    answer: str
    steps_used: int
    tools_called: list[str]


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
    agent = build_agent(user=current_user, db=db, hooks=hooks)

    with agent_run_span(
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
            content=result.final_step.text or "",
        )
    )

    return AgentAskResponse(
        answer=result.final_step.text or "",
        steps_used=result.final_step.index + 1,
        tools_called=[b.name for b in result.final_step.tools_used],
    )
