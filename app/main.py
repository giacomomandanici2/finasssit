import asyncio
import json
from pathlib import Path

from app.core.modelli import TransazioneInput
from app.core.classificatore import classifica_batch


def carica_transazioni(file_path: str) -> list[TransazioneInput]:
    path = Path(file_path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return [TransazioneInput(**item) for item in data]


async def main():
    txs = carica_transazioni("./app/data/sample_transazioni.json")

    risultati = await classifica_batch(txs)

    print("\nREPORT FINASSIST AI\n")

    for r in risultati:
        print(
            f"- ID: {r.id} | Importo: {r.importo} | "
            f"Rischio: {r.rischio} | Motivo: {r.motivazione}"
        )


if __name__ == "__main__":
    asyncio.run(main())