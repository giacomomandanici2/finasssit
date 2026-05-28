from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.repositories.base import BaseRepository
from app.models.message import Message
from app.models.chat_session import ChatSession


class MessagesRepository(BaseRepository):

    async def create(self, message: Message) -> Message:
        self.db.add(message)
        await self.db.flush()
        return message

    async def list_by_session(self, session_id: int) -> ChatSession | None:
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .options(selectinload(ChatSession.messages))
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()