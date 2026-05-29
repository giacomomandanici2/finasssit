from typing import TypedDict

from app.core.modelli import TransazioneInput


class ChatMessage(TypedDict):
    role: str
    content: str


def prompt_classifica_rischio_v1(tx: TransazioneInput) -> list[ChatMessage]:
    """Version 1 — Classifica il rischio di una transazione finanziaria
    in "basso", "medio" o "alto" in base a importo, descrizione e IBAN."""

    #     Prende una transazione e restituisce 2 messaggi:
    # - system: istruzioni per classificare il rischio della transazione come basso/medio/alto, con criteri (importo >10k, descrizione vaga, IBAN estero)
    # - user: i dati della transazione formattati (ID, IBAN, importo, descrizione, data)
    return [
        {
            "role": "system",
            "content": (
                "Sei un esperto di antiriciclaggio. Classifica il rischio della "
                "transazione come 'basso', 'medio' o 'alto'. "
                "Restituisci un oggetto JSON con i campi:\n"
                "- rischio: 'basso' | 'medio' | 'alto'\n"
                "- motivazione: stringa che spiega la decisione\n"
                "Criteri:\n"
                "- importi elevati (>10.000 €) aumentano il rischio\n"
                "- descrizioni vaghe o sospette (es. 'bonifico', 'giroconto', "
                "'operazione') aumentano il rischio\n"
                "- IBAN esteri o con pattern anomali aumentano il rischio\n"
                "- transazioni con descrizione chiara e importo contenuto "
                "sono a rischio basso"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Analizza la seguente transazione:\n"
                f"- ID: {tx.id}\n"
                f"- IBAN: {tx.iban}\n"
                f"- Importo: {tx.importo:.2f} €\n"
                f"- Descrizione: {tx.descrizione}\n"
                f"- Data: {tx.timestamp.isoformat()}"
            ),
        },
    ]
