"""Golden cases multi-agente: routing, role gating, tool execution."""

import pytest

from app.agents.team_factory import AgentTeamFactory, _ROLE_SPECIALIST_MAP
from app.agents.specialists.operations_agent import (
    build_operations_agent,
    make_invia_bonifico,
)
from app.agents.specialists.compliance_agent import (
    build_compliance_agent,
    verifica_aml,
)
from app.agents.specialists.rating_agent import (
    build_rating_agent,
    calcola_score,
)
from app.agents.exceptions import ToolForbidden, ToolError
from app.agents.rate_limit import RateLimitTracker, RateLimitExceeded
from app.models.user import User


# ──────────────────────────────────────────────
#  AgentTeamFactory — team composition per role
# ──────────────────────────────────────────────

class TestTeamFactory:
    """Verifica che il team di specialisti sia corretto per ogni ruolo."""

    def test_role_mapping_structure(self):
        assert _ROLE_SPECIALIST_MAP["retail"] == ["operations"]
        assert _ROLE_SPECIALIST_MAP["compliance"] == ["operations", "compliance"]
        assert _ROLE_SPECIALIST_MAP["admin"] == ["operations", "compliance", "rating"]

    def test_retail_gets_only_operations(self):
        user = User(id=1, username="retail_user", role="retail", password_hash="x")
        factory = AgentTeamFactory(user=user, db=None)
        team = factory.build_team()
        names = [a.name for a in team]
        assert names == ["operations_agent"]

    def test_compliance_gets_operations_and_compliance(self):
        user = User(id=2, username="compliance_user", role="compliance", password_hash="x")
        factory = AgentTeamFactory(user=user, db=None)
        team = factory.build_team()
        names = [a.name for a in team]
        assert names == ["operations_agent", "compliance_agent"]

    def test_admin_gets_all_three(self):
        user = User(id=3, username="admin", role="admin", password_hash="x")
        factory = AgentTeamFactory(user=user, db=None)
        team = factory.build_team()
        names = [a.name for a in team]
        assert names == ["operations_agent", "compliance_agent", "rating_agent"]

    def test_unknown_role_gets_empty_team(self):
        user = User(id=4, username="guest", role="guest", password_hash="x")
        factory = AgentTeamFactory(user=user, db=None)
        team = factory.build_team()
        assert team == []


# ──────────────────────────────────────────────
#  Operations Agent — tools
# ──────────────────────────────────────────────

class TestOperationsTools:
    """Golden case: 'qual è il mio saldo?' → operations_agent."""

    async def test_get_saldo_owned_iban(self):
        from app.agents.tools import make_get_saldo
        tool_fn = make_get_saldo("user_001")
        result = await tool_fn(iban="IT60X0542811101000000123456")
        assert "Saldo" in result
        assert "15.420" in result or "15,420" in result

    async def test_get_saldo_forbidden_iban(self):
        from app.agents.tools import make_get_saldo
        tool_fn = make_get_saldo("user_001")
        result = await tool_fn(iban="IT60X0542811101000000123458")
        assert "Accesso negato" in result or "non appartiene" in result

    async def test_invia_bonifico_idempotent(self):
        invia = make_invia_bonifico("user_001")
        r1 = await invia(
            iban_sorgente="IT60X0542811101000000123456",
            iban_destinazione="IT60X0542811101000000123457",
            importo=50.0,
            causale="test",
        )
        assert "Bonifico eseguito" in r1

        r2 = await invia(
            iban_sorgente="IT60X0542811101000000123456",
            iban_destinazione="IT60X0542811101000000123457",
            importo=50.0,
            causale="test",
        )
        assert "già eseguito" in r2

    async def test_invia_bonifico_insufficient_funds(self):
        invia = make_invia_bonifico("user_001")
        result = await invia(
            iban_sorgente="IT60X0542811101000000123456",
            iban_destinazione="IT60X0542811101000000123457",
            importo=999_999.0,
            causale="troppo",
        )
        assert "Saldo insufficiente" in result


# ──────────────────────────────────────────────
#  Compliance Agent — tools
# ──────────────────────────────────────────────

class TestComplianceTools:
    """Golden case: 'cosa dice la policy AML?' → compliance_agent."""

    async def test_verifica_aml_above_threshold(self):
        result = await verifica_aml(iban="IT60X0542811101000000123456", importo=15_000)
        assert "NON SUPERATA" in result
        assert "supera la soglia" in result

    async def test_verifica_aml_below_threshold(self):
        result = await verifica_aml(iban="IT60X0542811101000000123456", importo=100)
        assert "superata" in result.lower()
        assert "nessuna anomalia" in result.lower()

    async def test_verifica_aml_high_risk_country(self):
        result = await verifica_aml(iban="IR1234567890", importo=100)
        assert "NON SUPERATA" in result
        assert "alto rischio" in result.lower()

    async def test_verifica_aml_invalid_iban(self):
        result = await verifica_aml(iban="", importo=100)
        assert "IBAN non valido" in result


# ──────────────────────────────────────────────
#  Rating Agent — tools
# ──────────────────────────────────────────────

class TestRatingTools:
    """Golden case: 'score di Mario Rossi' → rating_agent."""

    async def test_calcola_score_known_cf(self):
        result = await calcola_score(codice_fiscale="RSSMRA85M01H501U")
        assert "Mario Rossi" in result
        assert "AAA" in result
        assert "850" in result

    async def test_calcola_score_unknown_cf(self):
        result = await calcola_score(codice_fiscale="ABCDEF12G34H567I")
        assert "Rating" in result
        assert "Score" in result

    async def test_calcola_score_invalid_cf(self):
        result = await calcola_score(codice_fiscale="")
        assert "non valido" in result.lower()


# ──────────────────────────────────────────────
#  Rate limit centralizzato
# ──────────────────────────────────────────────

class TestRateLimit:
    def test_tracker_consumes_steps(self):
        tracker = RateLimitTracker(max_steps=5)
        assert tracker.remaining == 5
        for _ in range(5):
            tracker.consume()
        assert tracker.remaining == 0

    def test_tracker_raises_when_exhausted(self):
        tracker = RateLimitTracker(max_steps=1)
        tracker.consume()
        with pytest.raises(RateLimitExceeded):
            tracker.consume()


# ──────────────────────────────────────────────
#  Security: role gating
# ──────────────────────────────────────────────

class TestRoleGating:
    """Solo compliance_lead può usare compliance_agent."""

    def test_compliance_agent_not_in_retail_team(self):
        user = User(id=1, username="retail_user", role="retail", password_hash="x")
        factory = AgentTeamFactory(user=user, db=None)
        team = factory.build_team()
        assert "compliance_agent" not in [a.name for a in team]

    def test_compliance_agent_in_compliance_team(self):
        user = User(id=2, username="compliance_user", role="compliance", password_hash="x")
        factory = AgentTeamFactory(user=user, db=None)
        team = factory.build_team()
        assert "compliance_agent" in [a.name for a in team]
