from typing import Annotated

from datapizza.agents import Agent
from datapizza.clients.factory import ClientFactory, Provider
from datapizza.tools import tool

from app.agents.exceptions import ToolError
from app.agents.tools import safe_tool

_SYSTEM_PROMPT = """Sei l'agente Rating. Calcola lo score di affidabilità
finanziaria per un cliente basandoti sul suo codice fiscale.

Regole:
- Rispondi sempre in italiano.
- Usa calcola_score per determinare lo score.
- Restituisci il rating in formato chiaro (AAA, AA, A, BBB, BB, B, CCC, D).
"""

_MOCK_SCORE_MAP: dict[str, tuple[str, str, int]] = {
    "RSSMRA85M01H501U": ("Mario Rossi", "AAA", 850),
    "VRDLGI92L05F205X": ("Luigi Verdi", "AA", 780),
    "BNCFRC88E30L736V": ("Franco Bianchi", "A", 720),
    "GLLLRA00A01H501U": ("Lara Gialli", "BBB", 680),
    "NNNMRL75B15F839P": ("Mario Neri", "BB", 620),
    "GRGLCA80T10A001X": ("Lucia Grigi", "B", 560),
    "RSSNRC90A01H501U": ("Enrico Rossi", "CCC", 480),
    "VRDLCA85B15F205Y": ("Carla Verdi", "D", 320),
}


@tool
@safe_tool
async def calcola_score(
    codice_fiscale: Annotated[str, "Codice fiscale del cliente da valutare"] = "",
) -> str:
    """Calcola lo score di affidabilità finanziaria per un codice fiscale."""
    cf = codice_fiscale.strip().upper()
    if not cf or len(cf) < 11:
        raise ToolError(
            f"Codice fiscale non valido: '{codice_fiscale}'",
            tool_name="calcola_score",
        )

    entry = _MOCK_SCORE_MAP.get(cf)
    if entry is None:
        # Mock deterministico basato sull'hash del CF
        hash_val = sum(ord(c) for c in cf)
        rating_list = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "D"]
        rating = rating_list[hash_val % len(rating_list)]
        score = max(150, min(950, hash_val % 800 + 150))
        return (
            f"**Calcolo Score per CF {cf}**\n"
            f"- Rating: {rating}\n"
            f"- Score: {score}/1000\n"
            f"- Giudizio: {'Ottimo' if rating in ('AAA','AA') else 'Buono' if rating == 'A' else 'Discreto' if rating == 'BBB' else 'Medio' if rating == 'BB' else 'Scarso' if rating == 'B' else 'Critico'}"
        )

    nome, rating, score = entry
    giudizio_map = {
        "AAA": "Ottimo", "AA": "Ottimo", "A": "Buono",
        "BBB": "Discreto", "BB": "Medio",
        "B": "Scarso", "CCC": "Critico", "D": "Critico",
    }
    return (
        f"**Calcolo Score per {nome}**\n"
        f"- Codice Fiscale: {cf}\n"
        f"- Rating: {rating}\n"
        f"- Score: {score}/1000\n"
        f"- Giudizio: {giudizio_map.get(rating, 'N/A')}"
    )


def build_rating_agent(
    client: ClientFactory | None = None,
    hooks=None,
) -> Agent:
    if client is None:
        client = ClientFactory.create(provider=Provider.MOCK, api_key="", model="mock")

    return Agent(
        name="rating_agent",
        client=client,
        description="Calcola lo score di rating finanziario per un codice fiscale.",
        system_prompt=_SYSTEM_PROMPT,
        tools=[calcola_score],
        max_steps=3,
        hooks=hooks,
    )
