from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

#qui creo la SessioneChat
from app.models.base import Base
class ChatSession(Base):
        __tablename__ = "chat_sessions"
        id: Mapped[int] = mapped_column(Integer, primary_key=True) # il mapped mi definisce il tipo di dato, il type hints
        user_id: Mapped[str] = mapped_column(String, index=True)
        created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

        messages = relationship(
        "Message",
        back_populates="session",
        lazy="raise" #modo di caricare le relazioni che mi obbliga a scrivere in maniera corretta le query
    )