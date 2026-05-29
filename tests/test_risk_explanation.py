from unittest.mock import AsyncMock

import pytest

from app.models.scored_transactions import ScoredTransaction
from app.services.risk_explanation import (
    RiskExplanationService,
    SpiegazioneRischio,
)


class LLMUnavailableError(Exception):
    """Simula l'indisponibilità del client LLM (circuit breaker aperto, rate limit, ecc.)."""
    ...


@pytest.fixture
def transazione_alta() -> ScoredTransaction:
    return ScoredTransaction(
        id=1,
        tx_id="tx-999",
        iban="IT60X0542811101000000123456",
        importo=20000.0,
        rischio="alto",
        motivazione="Bonifico sospetto",
    )


@pytest.fixture
def transazione_bassa() -> ScoredTransaction:
    return ScoredTransaction(
        id=2,
        tx_id="tx-888",
        iban="IT60X0542811101000000123456",
        importo=500.0,
        rischio="basso",
        motivazione="Stipendio mensile",
    )


@pytest.mark.asyncio
async def test_llm_restituisce_spiegazione(transazione_alta: ScoredTransaction):
    """Il servizio restituisce la spiegazione generata dall'LLM quando tutto funziona."""
    mock_llm = AsyncMock()
    mock_llm.chat.return_value = SpiegazioneRischio(
        spiegazione="Operazione ad alto rischio: bonifico estero di importo rilevante.",
        fattori=["importo > 10.000 €", "bonifico estero", "descrizione generica"],
    )

    service = RiskExplanationService(llm_client=mock_llm)
    risultato = await service.genera_spiegazione(transazione_alta)

    assert risultato.spiegazione == (
        "Operazione ad alto rischio: bonifico estero di importo rilevante."
    )
    assert len(risultato.fattori) == 3
    assert "importo > 10.000 €" in risultato.fattori
    mock_llm.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_rule_based_quando_llm_non_disponibile(
    transazione_alta: ScoredTransaction,
):
    """Se l'LLM solleva un'eccezione, il servizio torna alla spiegazione rule-based."""
    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = LLMUnavailableError("LLM non raggiungibile")

    service = RiskExplanationService(llm_client=mock_llm)
    risultato = await service.genera_spiegazione(transazione_alta)

    assert isinstance(risultato, SpiegazioneRischio)
    assert "importo elevato" in risultato.spiegazione
    assert any("importo elevato" in f for f in risultato.fattori)
    mock_llm.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_fallback_per_rischio_basso(transazione_bassa: ScoredTransaction):
    """Fallback per transazione a basso rischio."""
    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = LLMUnavailableError("LLM non raggiungibile")

    service = RiskExplanationService(llm_client=mock_llm)
    risultato = await service.genera_spiegazione(transazione_bassa)

    assert "basso" in risultato.spiegazione
    assert any("importo contenuto" in f for f in risultato.fattori)


@pytest.mark.asyncio
async def test_fallback_per_iban_estero():
    """Fallback rileva correttamente IBAN non italiano."""
    tx = ScoredTransaction(
        id=3,
        tx_id="tx-777",
        iban="DE89370400440532013000",
        importo=6000.0,
        rischio="medio",
        motivazione="Bonifico internazionale",
    )

    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = LLMUnavailableError("LLM non raggiungibile")

    service = RiskExplanationService(llm_client=mock_llm)
    risultato = await service.genera_spiegazione(tx)

    assert "estero" in risultato.spiegazione
    assert any("IBAN estero" in f for f in risultato.fattori)
