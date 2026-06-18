import logging

from datapizza.agents import Agent
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.team_factory import AgentTeamFactory
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


def build_triage_agent(
    user: User,
    db: AsyncSession,
    hooks=None,
) -> Agent:
    factory = AgentTeamFactory(user=user, db=db)
    specialists = factory.build_team()

    agent = Agent(
        name="triage_agent",
        client=factory.client,
        description="Instradamento richieste agli specialisti: operazioni, compliance, rating.",
        system_prompt=_SYSTEM_PROMPT,
        max_steps=3,
        hooks=hooks,
    )

    agent.can_call(specialists)

    return agent
