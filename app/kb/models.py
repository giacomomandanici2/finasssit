from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class KBChunk(Base):
    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    document_id: Mapped[str] = mapped_column(String, nullable=False)

    section: Mapped[str] = mapped_column(String, nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    embedding = mapped_column(Vector(1536), nullable=False)

    access_role: Mapped[str] = mapped_column(String, nullable=False)

    language: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
