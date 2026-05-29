from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TransazioneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tx_id: str
    iban: str
    importo: float
    rischio: str
    motivazione: str | None = None
    created_at: datetime
