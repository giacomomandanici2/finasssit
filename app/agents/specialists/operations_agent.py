import uuid
from typing import Annotated

from datapizza.agents import Agent
from datapizza.clients.factory import ClientFactory, Provider
from datapizza.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.exceptions import ToolError, ToolForbidden
from app.agents.tools import _MOCK_SALDI, _USER_IBANS, safe_tool
from app.repositories.transaction import TransactionsRepository

_SYSTEM_PROMPT = """Sei l'agente Operazioni Bancarie. Gestisci saldi,
storico transazioni e bonifici per conto dell'utente.

Regole:
- Rispondi sempre in italiano.
- Usa get_saldo per verificare la disponibilità prima di un bonifico.
- Usa storico_transazioni per mostrare i movimenti recenti.
- Per inviare un bonifico usa invia_bonifico con una idempotency_key unica.
- Non inventare IBAN. Se non hai un IBAN valido, chiedilo all'utente.
- Se l'IBAN non appartiene all'utente, nega l'accesso.
"""


def make_invia_bonifico(user_id: str):
    _processed: set[str] = set()

    @tool
    @safe_tool
    async def invia_bonifico(
        iban_sorgente: Annotated[str, "IBAN da cui prelevare i fondi"] = "",
        iban_destinazione: Annotated[str, "IBAN destinatario del bonifico"] = "",
        importo: Annotated[float, "Importo del bonifico in EUR"] = 0.0,
        idempotency_key: Annotated[
            str,
            "Chiave univoca per garantire l'idempotenza del bonifico. "
            "Se riutilizzi la stessa key, la richiesta viene ignorata.",
        ] = "",
    ) -> str:
        """Invia un bonifico da un IBAN sorgente a un IBAN destinatario.
        Idempotente: stessa idempotency_key → operazione già eseguita."""
        if not idempotency_key:
            raise ToolError("idempotency_key obbligatoria per invia_bonifico", tool_name="invia_bonifico")

        idempotency_hash = f"{user_id}:{idempotency_key}"
        if idempotency_hash in _processed:
            return "Bonifico già eseguito in precedenza (idempotency key già processata)."

        iban_src = iban_sorgente.strip().replace(" ", "")
        iban_dst = iban_destinazione.strip().replace(" ", "")

        owned = _USER_IBANS.get(user_id, [])
        if iban_src not in owned:
            raise ToolForbidden(
                f"L'IBAN {iban_src} non appartiene all'utente corrente",
                tool_name="invia_bonifico",
            )

        saldo = _MOCK_SALDI.get(iban_src, 0.0)
        if saldo < importo:
            raise ToolError(
                f"Saldo insufficiente su {iban_src}: disponibili € {saldo:,.2f}, "
                f"richiesti € {importo:,.2f}",
                tool_name="invia_bonifico",
            )

        _MOCK_SALDI[iban_src] = saldo - importo
        _processed.add(idempotency_hash)

        return (
            f"Bonifico eseguito: € {importo:,.2f} da {iban_src} a {iban_dst}. "
            f"Nuovo saldo {iban_src}: € {_MOCK_SALDI[iban_src]:,.2f}. "
            f"ID richiesta: {idempotency_key}"
        )

    return invia_bonifico


def build_operations_agent(
    user_id: str,
    db: AsyncSession,
    client: ClientFactory | None = None,
) -> Agent:
    if client is None:
        client = ClientFactory.create(provider=Provider.MOCK, api_key="", model="mock")

    from app.agents.tools import make_get_saldo, make_storico_transazioni

    tools = [
        make_get_saldo(user_id=user_id),
        make_storico_transazioni(user_id=user_id, db=db),
        make_invia_bonifico(user_id=user_id),
    ]

    return Agent(
        name="operations_agent",
        client=client,
        description="Gestisce operazioni bancarie: saldo, storico transazioni, bonifici.",
        system_prompt=_SYSTEM_PROMPT,
        tools=tools,
        max_steps=4,
    )
