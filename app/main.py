

from pathlib import Path

from app.core.modelli import TransazioneInput


def carica_transazioni(file_path: str) -> list[TransazioneInput]:
    sample_path = Path(file_path)
    


async def main():
    print("Transazioni test")
