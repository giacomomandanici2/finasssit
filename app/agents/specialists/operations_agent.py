import hashlib
from typing import Annotated

from datapizza.agents import Agent
from datapizza.clients.factory import ClientFactory, Provider
from datapizza.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.exceptions import ToolError, ToolForbidden
from app.agents.tools import _MOCK_SALDI, _USER_IBANS, safe_tool
from app.core.redis import get_redis

_IDEMP_TTL_SECONDS = 3600

_SYSTEM_PROMPT = """Sei l'agente Operazioni Bancarie. Gestisci saldi,
storico transazioni e bonifici per conto dell'utente.

Regole:
- Rispondi sempre in italiano.
- Usa get_saldo per verificare la disponibilità prima di un bonifico.
- Usa storico_transazioni per mostrare i movimenti recenti.
- Per inviare un bonifico usa invia_bonifico con una causale descrittiva.
- Non inventare IBAN. Se non hai un IBAN valido, chiedilo all'utente.
- Se l'IBAN non appartiene all'utente, nega l'accesso.
"""


def _make_idemp_key(user_id: str, iban_src: str, iban_dst: str, importo: float, causale: str) -> str:
    raw = f"{user_id}|{iban_src}|{iban_dst}|{importo}|{causale}"
    return hashlib.sha256(raw.encode()).hexdigest()


def make_invia_bonifico(user_id: str):
    _processed: set[str] = set()

    @tool
    @safe_tool
    async def invia_bonifico(
        iban_sorgente: Annotated[str, "IBAN da cui prelevare i fondi"] = "",
        iban_destinazione: Annotated[str, "IBAN destinatario del bonifico"] = "",
        importo: Annotated[float, "Importo del bonifico in EUR"] = 0.0,
        causale: Annotated[str, "Causale / descrizione del bonifico"] = "",
    ) -> str:
        """Invia un bonifico da un IBAN sorgente a un IBAN destinatario.
        Idempotente: la stessa operazione (stessi parametri) viene eseguita
        una sola volta entro 1 ora."""
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

        idemp_key = _make_idemp_key(user_id, iban_src, iban_dst, importo, causale)
        redis_key = f"bonifico:idemp:{idemp_key}"

        redis = get_redis()
        if redis is not None:
            already = await redis.set(redis_key, "1", nx=True, ex=_IDEMP_TTL_SECONDS)
            if already is None:
                return (
                    f"Bonifico già eseguito in precedenza (operazione identica "
                    f"negli ultimi {_IDEMP_TTL_SECONDS // 3600}h)."
                )
        else:
            if idemp_key in _processed:
                return "Bonifico già eseguito in precedenza."
            _processed.add(idemp_key)

        _MOCK_SALDI[iban_src] = saldo - importo

        return (
            f"Bonifico eseguito: € {importo:,.2f} da {iban_src} a {iban_dst}. "
            f"Causale: {causale or 'nessuna'}. "
            f"Nuovo saldo {iban_src}: € {_MOCK_SALDI[iban_src]:,.2f}."
        )

    return invia_bonifico


def build_operations_agent(
    user_id: str,
    db: AsyncSession,
    client: ClientFactory | None = None,
    hooks=None,
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
        hooks=hooks,
    )
