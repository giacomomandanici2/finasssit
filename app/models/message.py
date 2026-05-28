from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

#qui creo il modello Message
from app.models.base import Base
from app.models.chat_session import ChatSession
class Message(Base):
        __tablename__ = "messages"
        id: Mapped[int] = mapped_column(Integer, primary_key=True) # il mapped mi definisce il tipo di dato, il type hints
        session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"))
        role: Mapped[str] = mapped_column(String)
        content: Mapped[str] = mapped_column(Text)        
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

        session: Mapped["ChatSession"] = relationship(back_populates="messages")
