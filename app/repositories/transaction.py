from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.scored_transactions import ScoredTransaction


class TransactionsRepository(BaseRepository):

#UPDATE se esiste, INSERT se non esiste
    async def upsert(self, tx: ScoredTransaction) -> ScoredTransaction:
        existing = await self.get_by_tx_id(tx.tx_id)

        if existing:
            existing.iban = tx.iban
            existing.importo = tx.importo
            existing.rischio = tx.rischio
            existing.motivazione = tx.motivazione
            obj = existing
        else:
            self.db.add(tx)
            obj = tx

        await self.db.flush()
        return obj

    async def get_by_tx_id(self, tx_id: str):
        stmt = select(ScoredTransaction).where(
            ScoredTransaction.tx_id == tx_id
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 20):
        stmt = (
            select(ScoredTransaction)
            .order_by(ScoredTransaction.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return result.scalars().all()