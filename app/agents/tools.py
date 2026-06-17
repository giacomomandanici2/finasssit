from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from datapizza.tools import tool
from app.agents.reference_data import lookup_iban_country
from app.rag.service import RAGService
from app.repositories.transaction import TransactionsRepository

_MOCK_SALDI: dict[str, float] = {
    "IT60X0542811101000000123456": 15420.50,
    "IT60X0542811101000000123457": 3200.00,
    "IT60X0542811101000000123458": 89000.00,
    "DE89370400440532013000": 12500.00,
    "FR1420041010050500013M02606": 6700.00,
    "GB29NWBK60161331926819": 25000.00,
}

_USER_IBANS: dict[str, list[str]] = {
    "user_001": [
        "IT60X0542811101000000123456",
        "IT60X0542811101000000123457",
    ],
    "user_002": [
        "IT60X0542811101000000123458",
        "DE89370400440532013000",
    ],
    "user_003": [
        "FR1420041010050500013M02606",
        "GB29NWBK60161331926819",
    ],
}


def make_get_saldo(user_id: str):
    @tool
    async def get_saldo(
        iban: Annotated[str, "IBAN di cui ottenere il saldo"] = "",
    ) -> str:
        """Ottiene il saldo corrente per un IBAN (dati mock)."""
        iban_clean = iban.strip().replace(" ", "")
        owned = _USER_IBANS.get(user_id, [])
        if iban_clean not in owned:
            return (
                f"Accesso negato: l'IBAN {iban_clean} "
                f"non appartiene all'utente corrente"
            )
        saldo = _MOCK_SALDI.get(iban_clean)
        if saldo is None:
            return f"Nessun saldo disponibile per l'IBAN {iban_clean}"
        return f"Saldo per {iban_clean}: € {saldo:,.2f}"

    return get_saldo


def make_cerca_documenti(db: AsyncSession, role: str = "retail"):
    @tool
    async def cerca_documenti(
        query: Annotated[
            str,
            "Query di ricerca testuale nel knowledge base aziendale",
        ] = "",
    ) -> str:
        """Cerca documenti nel knowledge base filtrati per ruolo utente."""
        svc = RAGService(db=db, user_role=role)
        result = await svc.ask(query)
        return result.answer

    return cerca_documenti


@tool
async def paese_da_iban(
    iban: Annotated[str, "IBAN da analizzare (può contenere spazi)"] = "",
) -> str:
    """Determina il paese di origine di un IBAN in modo deterministico."""
    return lookup_iban_country(iban=iban)


def make_storico_transazioni(user_id: str, db: AsyncSession):
    @tool
    async def storico_transazioni(
        iban: Annotated[
            str,
            "IBAN di cui visualizzare lo storico transazioni",
        ] = "",
        limit: Annotated[int, "Numero massimo di transazioni"] = 10,
    ) -> str:
        """Recupera lo storico delle transazioni per un IBAN dal database."""
        iban_clean = iban.strip().replace(" ", "")
        owned = _USER_IBANS.get(user_id, [])
        if iban_clean not in owned:
            return (
                f"Accesso negato: l'IBAN {iban_clean} "
                f"non appartiene all'utente corrente"
            )
        repo = TransactionsRepository(db)
        transactions = await repo.list_recent(limit=limit)
        txs = [t for t in transactions if t.iban == iban_clean]
        if not txs:
            return f"Nessuna transazione trovata per l'IBAN {iban_clean}"
        lines = [f"**Storico transazioni per {iban_clean}:**"]
        for t in txs:
            lines.append(
                f"- ID: {t.tx_id} | Importo: € {t.importo:,.2f} | "
                f"Rischio: {t.rischio} | Data: {t.created_at.isoformat()}"
            )
            if t.motivazione:
                lines.append(f"  Motivo: {t.motivazione}")
        return "\n".join(lines)

    return storico_transazioni
