import logging

from datapizza.agents import Agent, AgentHooks
from datapizza.clients.factory import ClientFactory, Provider
from datapizza.clients.mock_client import MockClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import (
    make_cerca_documenti,
    make_get_saldo,
    make_storico_transazioni,
    paese_da_iban,
)
from app.agents.tracing import get_tracer
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sei FinAssist AI, l'assistente virtuale di banca per l'analisi finanziaria.

Regole:
- Rispondi sempre in italiano.
- Usa gli strumenti a disposizione per ottenere dati reali (saldo, storico transazioni, documenti).
- Non inventare MAI codici IBAN. Se non hai un IBAN valido dall'utente, chiedilo esplicitamente.
- Per determinare il paese di un IBAN usa l'apposito strumento.
- Se un IBAN non appartiene all'utente corrente, comunica che non hai accesso.
- Se un'operazione va in errore, spiega il motivo all'utente in modo chiaro."""  # noqa: E501


def _build_client() -> MockClient:
    if settings.azure_openai_endpoint and settings.azure_openai_key:
        try:
            base_url = (
                f"{settings.azure_openai_endpoint}"
                f"/openai/deployments/{settings.azure_openai_deployment}"
            )
            return ClientFactory.create(
                provider=Provider.OPENAI,
                api_key=settings.azure_openai_key,
                model=settings.azure_openai_deployment,
                base_url=base_url,
                default_query={"api-version": settings.azure_openai_api_version},
            )
        except Exception as exc:
            logger.warning("Failed to create OpenAI client, falling back to MockClient: %s", exc)

    return ClientFactory.create(
        provider=Provider.MOCK,
        api_key="",
        model="mock",
    )


def build_agent(
    user: User,
    db: AsyncSession,
    hooks: AgentHooks | None = None,
) -> Agent:
    client = _build_client()

    user_id = f"user_{user.id:03d}"

    tools = [
        make_get_saldo(user_id=user_id),
        paese_da_iban,
        make_cerca_documenti(db=db, role=user.role),
        make_storico_transazioni(user_id=user_id, db=db),
    ]

    agent = Agent(
        name="finassist",
        client=client,
        system_prompt=_SYSTEM_PROMPT,
        tools=tools,
        max_steps=6,
        hooks=hooks,
    )

    return agent
