import asyncio
from app.schemas.transactions import TransactionIn, TransactionScored
from app.core.config import Settings



# qui faccio la logica per le chiamate endpoint
class ScoringService:
    def __init__(self, settings: Settings):
        self.settings = settings
    
    async def post_score(self, trx: TransactionIn) -> TransactionScored:
        await asyncio.sleep(0.1)
        if trx.importo > self.settings.scoring_threshold_high:
            rischio = "HIGH"
            score = 90
        elif trx.importo > self.settings.scoring_threshold_medium:
            rischio = "MEDIUM"
            score = 60
        else:
            rischio = "LOW"
            score = 20
        return TransactionScored(
            **trx.model_dump(),
            rischio = rischio,
            score = score
        )
    
    async def post_score_batch(self, transazioni:list [TransactionIn]) -> list [TransactionScored]:
        tasks = [self.post_score(tx) for tx in transazioni]
        return await asyncio.gather(*tasks)    
    
