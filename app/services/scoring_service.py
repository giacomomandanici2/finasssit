from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scored_transactions import ScoredTransaction
from app.repositories.transaction import TransactionsRepository
from app.schemas import TransactionIn, TransactionScored, FasciaRischio
class ScoringService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = TransactionsRepository(db)

    async def score_and_persist(self, trx: TransactionIn) -> TransactionScored:
        try:
            # 1. LOGICA DI SCORING
            if trx.importo > 10_000:
                rischio = FasciaRischio.HIGH
                score = 90
            elif trx.importo > 5_000:
                rischio = FasciaRischio.MEDIUM
                score = 60
            else:
                rischio = FasciaRischio.LOW
                score = 20

            # 2. CREA ENTITÀ ORM (IMPORTANTISSIMO)
            db_obj = ScoredTransaction(
                tx_id=trx.id,
                iban="N/A",  # dipende dal tuo schema reale
                importo=trx.importo,
                rischio=rischio,
                motivazione=trx.descrizione
            )

            # 3. SALVA VIA REPOSITORY
            await self.repo.upsert(db_obj)

            # 4. COMMIT (BOUNDARY TRANSAZIONE)
            await self.db.commit()

            # 5. RETURN RESPONSE API
            return TransactionScored(
                transazione=trx,
                fascia=rischio,
                score=score
            )

        except Exception:
            await self.db.rollback()
            raise