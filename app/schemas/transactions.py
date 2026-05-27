"""Schema dei request/response per l'API transactions."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

class Causale(StrEnum):
    BONIFICO_SEPA = "bonifico_sepa"
    BONIFICO_ESTERO = "bonifico_estero"
    PRELIEVO_ATM = "prelievo_atm"
    PRELIEVO_ATM_ALTRO = "prelievo_atm_altro_istituto"
    ADDEBITO_DIRETTO = "addebito_diretto"
    

    


class FasciaRischio(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"




class TransactionRequest(BaseModel):
    """Payload di una transazione da classificare."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: Annotated[str, Field(pattern=r"^TXN\d{6}$")]
    importo: Annotated[Decimal, Field(decimal_places=2)]
    causale: Causale
    data: datetime
    iban_contropartita: str | None = None
    paese_contropartita: str | None = None

"""class TransactionIn"""
class TransactionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: Annotated[str, Field(pattern=r"^TXN\d{6}$")]
    importo: float = Field(gt=0)
    descrizione: str
    timestamp: datetime


class TransactionScored(BaseModel):
    """Risposta: transazione con score e fascia di rischio."""
    rischio: FasciaRischio
    score:int = Field(ge = 0, le=100)


class BatchScoreRequest(BaseModel):
    """Richiesta di scoring batch."""

    model_config = ConfigDict(extra="forbid")

    transazioni: Annotated[
        list[TransactionRequest], Field(min_length=1, max_length=500)
    ]


class BatchScoreResponse(BaseModel):
    """Risposta di scoring batch (sintetica)."""

    totale_input: int
    totale_classificate: int
    classificate: list[TransactionScored]
    errori: list[dict]
