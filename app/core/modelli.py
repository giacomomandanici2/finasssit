from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)


class TransazioneInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    id: str
    iban: str
    importo: Annotated[float, Field(gt=0)]
    descrizione: str
    timestamp: datetime

    @field_validator("iban", mode="before")
    @classmethod
    def normalizza_iban(cls, v: str) -> str:
        return v.replace(" ", "").upper()


class TransazioneScored(TransazioneInput):
    rischio: Literal["basso", "medio", "alto"]
    motivazione: str

    @computed_field
    @property
    def iban_mascherato(self) -> str:
        iban = self.iban
        return iban[:2] + "****" + iban[-4:]