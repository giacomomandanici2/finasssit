from typing import Annotated

from datapizza.tools import tool
from app.agents.exceptions import ToolError

_IBAN_COUNTRY_MAP = {
    "AD": "Andorra",
    "AE": "United Arab Emirates",
    "AL": "Albania",
    "AT": "Austria",
    "AZ": "Azerbaijan",
    "BA": "Bosnia and Herzegovina",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "BH": "Bahrain",
    "BR": "Brazil",
    "BY": "Belarus",
    "CH": "Switzerland",
    "CR": "Costa Rica",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DK": "Denmark",
    "DO": "Dominican Republic",
    "EE": "Estonia",
    "EG": "Egypt",
    "ES": "Spain",
    "FI": "Finland",
    "FO": "Faroe Islands",
    "FR": "France",
    "GB": "United Kingdom",
    "GE": "Georgia",
    "GI": "Gibraltar",
    "GL": "Greenland",
    "GR": "Greece",
    "GT": "Guatemala",
    "HR": "Croatia",
    "HU": "Hungary",
    "IE": "Ireland",
    "IL": "Israel",
    "IQ": "Iraq",
    "IS": "Iceland",
    "IT": "Italy",
    "JO": "Jordan",
    "KW": "Kuwait",
    "KZ": "Kazakhstan",
    "LB": "Lebanon",
    "LC": "Saint Lucia",
    "LI": "Liechtenstein",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "LY": "Libya",
    "MC": "Monaco",
    "MD": "Moldova",
    "ME": "Montenegro",
    "MK": "North Macedonia",
    "MR": "Mauritania",
    "MT": "Malta",
    "MU": "Mauritius",
    "NL": "Netherlands",
    "NO": "Norway",
    "PK": "Pakistan",
    "PL": "Poland",
    "PS": "Palestine",
    "PT": "Portugal",
    "QA": "Qatar",
    "RO": "Romania",
    "RS": "Serbia",
    "RU": "Russia",
    "SA": "Saudi Arabia",
    "SC": "Seychelles",
    "SD": "Sudan",
    "SE": "Sweden",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "SM": "San Marino",
    "ST": "São Tomé and Príncipe",
    "SV": "El Salvador",
    "TL": "Timor-Leste",
    "TN": "Tunisia",
    "TR": "Turkey",
    "UA": "Ukraine",
    "VA": "Vatican City",
    "VG": "British Virgin Islands",
    "XK": "Kosovo",
}


@tool
def lookup_iban_country(
    iban: Annotated[str, "IBAN da analizzare (può contenere spazi)"] = "",
) -> str:
    """Estrae il paese di origine da un IBAN in modo deterministico."""
    code = iban.strip().replace(" ", "")[:2].upper()
    if len(code) < 2 or not code.isalpha():
        raise ToolError(
            "IBAN non valido: i primi due caratteri devono essere lettere",
            tool_name="lookup_iban_country",
        )
    country = _IBAN_COUNTRY_MAP.get(code)
    if country is None:
        raise ToolError(
            f"Paese sconosciuto per codice: {code}",
            tool_name="lookup_iban_country",
        )
    return country
