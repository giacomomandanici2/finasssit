import logging

from datapizza.agents import Agent
from datapizza.clients.factory import ClientFactory, Provider
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.specialists.compliance_agent import build_compliance_agent
from app.agents.specialists.operations_agent import build_operations_agent
from app.agents.specialists.rating_agent import build_rating_agent
from app.agents.tracing import get_tracer
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sei l'agente di triage di FinAssist AI. Il tuo compito
è analizzare la richiesta dell'utente e delegarla allo specialista corretto.

Specialisti disponibili:
- operations_agent: saldo, storico transazioni, bonifici (operazioni bancarie).
- compliance_agent: verifica AML, documenti normativi e policy.
- rating_agent: calcolo score finanziario e rating.

Regole:
- Rispondi sempre in italiano.
- Analizza la richiesta e chiama lo specialista più appropriato.
- Se la richiesta riguarda più ambiti, chiama più specialisti in sequenza.
- Non superare MAI 2 livelli di profondità (triage → specialista).
- Riporta all'utente il risultato finale in modo chiaro.
- Se non sai cosa fare, chiedi chiarimenti all'utente.
"""


def _build_client():
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


def build_triage_agent(
    user: User,
    db: AsyncSession,
    hooks=None,
) -> Agent:
    client = _build_client()
    user_id = f"user_{user.id:03d}"

    operations = build_operations_agent(user_id=user_id, db=db)
    compliance = build_compliance_agent(db=db)
    rating = build_rating_agent()

    agent = Agent(
        name="triage_agent",
        client=client,
        description="Agente di triage che analizza le richieste e le indirizza allo specialista corretto.",
        system_prompt=_SYSTEM_PROMPT,
        max_steps=8,
        hooks=hooks,
    )

    agent.can_call([operations, compliance, rating])

    return agent
