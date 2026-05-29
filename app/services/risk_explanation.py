from typing import Any

from pydantic import BaseModel

from app.ai.llm import get_llm, CircuitBreakerOpenError
from app.ai.redaction import redigi
from app.ai.prompts import ChatMessage
from app.models.scored_transactions import ScoredTransaction


class SpiegazioneRischio(BaseModel):
    spiegazione: str
    fattori: list[str]


class RiskExplanationService:
    def __init__(
        self,
        llm_client: Any | None = None,
    ) -> None:
        self._llm = llm_client
        self._get_llm = get_llm

    async def genera_spiegazione(self, tx: ScoredTransaction) -> SpiegazioneRischio:
        try:
            return await self._spiegazione_llm(tx)
        except (CircuitBreakerOpenError, ValueError, Exception):
            return self._spiegazione_fallback(tx)

    async def _spiegazione_llm(self, tx: ScoredTransaction) -> SpiegazioneRischio:
        llm = self._llm or self._get_llm()

        descrizione = getattr(tx, "motivazione", "bonifico") or "bonifico"
        messaggi: list[ChatMessage] = [
            {
                "role": "system",
                "content": (
                    "Sei un esperto di antiriciclaggio. Spiega perché una "
                    "transazione è stata classificata con un certo livello di "
                    "rischio. Restituisci un JSON con:\n"
                    "- spiegazione: spiegazione chiara in italiano\n"
                    "- fattori: lista dei fattori di rischio identificati"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Transazione:\n"
                    f"- IBAN: {tx.iban}\n"
                    f"- Importo: {tx.importo:.2f} €\n"
                    f"- Descrizione: {descrizione}\n"
                    f"- Rischio assegnato: {tx.rischio}"
                ),
            },
        ]
        messaggi_redatti = [
            {"role": m["role"], "content": redigi(m["content"])}
            for m in messaggi
        ]
        return await llm.chat(messaggi_redatti, SpiegazioneRischio)

    def _spiegazione_fallback(self, tx: ScoredTransaction) -> SpiegazioneRischio:
        fattori: list[str] = []

        if tx.importo > 10_000:
            fattori.append("importo elevato (> 10.000 €)")
        elif tx.importo > 5_000:
            fattori.append("importo moderato (5.000 – 10.000 €)")

        if not tx.iban.startswith("IT"):
            fattori.append("IBAN estero")

        if tx.rischio in ("alto", "medio"):
            if not fattori:
                fattori.append("valutazione interna del rischio")
            spiegazione = (
                f"Transazione classificata come rischiosa a causa "
                f"dei seguenti fattori: {', '.join(fattori)}."
            )
        else:
            if not fattori:
                fattori.append("importo contenuto e IBAN nazionale")
            spiegazione = (
                "Nessun fattore di rischio significativo rilevato. "
                "Transazione considerata a basso rischio."
            )

        return SpiegazioneRischio(spiegazione=spiegazione, fattori=fattori)
