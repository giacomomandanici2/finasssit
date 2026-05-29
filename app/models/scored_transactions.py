from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ScoredTransaction(Base):
    __tablename__ = "scored_transactions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    tx_id: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    iban: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    importo: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    rischio: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    motivazione: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )