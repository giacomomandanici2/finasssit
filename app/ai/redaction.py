import re

# IT + 2 cifre di controllo + CIN + 5 ABI + 5 CAB + 12 conto (alfanumerico)
_IBAN_COMPATTO = re.compile(r"\bIT\d{2}[A-Z]\d{5}\d{5}[A-Z0-9]{12}\b")
# Formato con spaziature comuni: ITkk AAAA BBBB CCCC DDDD EEE FFF
_IBAN_SPAZI = re.compile(
    r"\bIT\d{2}[ ]"
    r"[A-Z0-9]{4}[ ]"
    r"\d{4}[ ]"
    r"\d{4}[ ]"
    r"\d{4}[ ]"
    r"\d{4}[ ]"
    r"\d{3}\b"
)

CF_PATTERN = re.compile(r"\b[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]\b")


def _maschera_iban(m: re.Match) -> str:
    iban = m.group(0).replace(" ", "")
    return iban[:4] + "*" * (len(iban) - 8) + iban[-4:]


def _maschera_cf(m: re.Match) -> str:
    cf = m.group(0)
    return cf[:3] + "*" * (len(cf) - 6) + cf[-3:]


def redigi(testo: str) -> str:
    """Maschera IBAN e codici fiscali presenti nel testo prima dell'invio all'LLM."""
    testo = _IBAN_COMPATTO.sub(_maschera_iban, testo)
    testo = _IBAN_SPAZI.sub(_maschera_iban, testo)
    testo = CF_PATTERN.sub(_maschera_cf, testo)
    return testo
