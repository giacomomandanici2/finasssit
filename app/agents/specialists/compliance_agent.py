from typing import Annotated

from datapizza.agents import Agent
from datapizza.clients.factory import ClientFactory, Provider
from datapizza.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.exceptions import ToolError
from app.agents.tools import safe_tool

_SYSTEM_PROMPT = """Sei l'agente Compliance. Verifica operazioni
sospette e consulta la documentazione normativa.

Regole:
- Rispondi sempre in italiano.
- Usa cerca_documenti per consultare le policy aziendali.
- Usa verifica_aml per controllare se un'operazione è sospetta.
- Se un'operazione supera i 10.000 € o proviene da paesi ad alto rischio,
  segnalala come sospetta.
"""


@tool
@safe_tool
async def verifica_aml(
    iban: Annotated[str, "IBAN da verificare"] = "",
    importo: Annotated[float, "Importo dell'operazione in EUR"] = 0.0,
) -> str:
    """Verifica antiriciclaggio (AML) su un'operazione bancaria."""
    iban_clean = iban.strip().replace(" ", "")
    if not iban_clean:
        raise ToolError("IBAN non valido", tool_name="verifica_aml")

    soglia = 10_000.0
    paesi_rischio = {"IR", "KP", "SY", "CU", "MM"}

    codice_paese = iban_clean[:2].upper()
    exceeds_threshold = importo > soglia
    high_risk_country = codice_paese in paesi_rischio

    alerts = []
    if exceeds_threshold:
        alerts.append(f"importo € {importo:,.2f} supera la soglia di € {soglia:,.2f}")
    if high_risk_country:
        alerts.append(f"paese {codice_paese} classificato ad alto rischio")

    if not alerts:
        return (
            f"Verifica AML superata per {iban_clean}: "
            f"nessuna anomalia rilevata (importo € {importo:,.2f})."
        )

    return (
        f"VERIFICA AML NON SUPERATA per {iban_clean}:\n"
        + "\n".join(f"- {a}" for a in alerts)
        + "\nSi raccomanda di bloccare l'operazione e approfondire."
    )


def build_compliance_agent(
    db: AsyncSession,
    client: ClientFactory | None = None,
    hooks=None,
) -> Agent:
    if client is None:
        client = ClientFactory.create(provider=Provider.MOCK, api_key="", model="mock")

    from app.agents.tools import make_cerca_documenti

    tools = [
        make_cerca_documenti(db=db, role="compliance"),
        verifica_aml,
    ]

    return Agent(
        name="compliance_agent",
        client=client,
        description="Gestisce compliance e antiriciclaggio: verifica AML, documenti normativi.",
        system_prompt=_SYSTEM_PROMPT,
        tools=tools,
        max_steps=4,
        hooks=hooks,
    )
