import logging

from datapizza.agents import Agent
from datapizza.clients.factory import ClientFactory, Provider
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.specialists.compliance_agent import build_compliance_agent
from app.agents.specialists.operations_agent import build_operations_agent
from app.agents.specialists.rating_agent import build_rating_agent
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sei un agente di triage. Il tuo unico compito è
analizzare la richiesta dell'utente e delegarla allo specialista corretto.

Specialisti:
- operations_agent: saldo, storico transazioni, bonifici.
- compliance_agent: verifica AML, documenti normativi.
- rating_agent: calcolo score finanziario e rating.

Regole:
- Analizza la richiesta e chiama UNO specialista.
- Se la richiesta tocca più ambiti, chiamali in sequenza.
- Non superare MAI 2 livelli di profondità.
- Non rispondere direttamente: usa sempre uno specialista.
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
        description="Instradamento richieste agli specialisti: operazioni, compliance, rating.",
        system_prompt=_SYSTEM_PROMPT,
        max_steps=3,
        hooks=hooks,
    )

    agent.can_call([operations, compliance, rating])

    return agent
