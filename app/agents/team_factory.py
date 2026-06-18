import logging

from datapizza.agents import Agent
from datapizza.clients.factory import ClientFactory, Provider
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.specialists.compliance_agent import build_compliance_agent
from app.agents.specialists.operations_agent import build_operations_agent
from app.agents.specialists.rating_agent import build_rating_agent
from app.agents.tracing import TracingHooks, get_tracer
from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

_ROLE_SPECIALIST_MAP: dict[str, list[str]] = {
    "retail": ["operations"],
    "compliance": ["operations", "compliance"],
    "admin": ["operations", "compliance", "rating"],
}


class AgentTeamFactory:
    def __init__(self, user: User, db: AsyncSession):
        self._user = user
        self._db = db
        self._user_id = f"user_{user.id:03d}"
        self.client = self._build_client()
        self._tracer = get_tracer()

    def _build_client(self):
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
                logger.warning(
                    "Failed to create OpenAI client, falling back to MockClient: %s", exc
                )
        return ClientFactory.create(
            provider=Provider.MOCK,
            api_key="",
            model="mock",
        )

    def build_team(
        self,
        hooks=None,
        rate_limit_tracker=None,
    ) -> list[Agent]:
        specialists = _ROLE_SPECIALIST_MAP.get(self._user.role, [])
        agents: list[Agent] = []

        def _make_hooks(agent_name: str):
            if hooks is not None:
                return hooks
            return TracingHooks(
                tracer=self._tracer,
                rate_limit_tracker=rate_limit_tracker,
                agent_name=agent_name,
            )

        if "operations" in specialists:
            agents.append(
                build_operations_agent(
                    user_id=self._user_id,
                    db=self._db,
                    client=self.client,
                    hooks=_make_hooks("operations"),
                )
            )
        if "compliance" in specialists:
            agents.append(
                build_compliance_agent(
                    db=self._db,
                    client=self.client,
                    hooks=_make_hooks("compliance"),
                )
            )
        if "rating" in specialists:
            agents.append(
                build_rating_agent(
                    client=self.client,
                    hooks=_make_hooks("rating"),
                )
            )

        return agents
