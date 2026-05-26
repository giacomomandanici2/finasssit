import asyncio

from app.core.modelli import TransazioneInput, TransazioneScored


async def classifica_singola_transazione(transazione: TransazioneInput) -> TransazioneScored:
    # Simulazione di un processo di classificazione che potrebbe essere lento
    await asyncio.sleep(0.1) #simula un ritardo
    if(transazione.importo > 10_000):
        rischio="alto"
        motivazione="Importo superiroe a 10.000"
    elif(transazione.importo > 1_000):
        rischio="medio"
        motivazione="Importo superiore a 1.000"
    else:
        rischio="basso"
        motivazione="Importo inferiore o uguale a 1.000"

    return (TransazioneScored(rischio = rischio, motivazione = motivazione, **transazione.model_dump()))     #crea un nuovo oggetto TransazioneScored usando i campi di TransazioneInput e aggiungendo rischio e motivazione

async def classifica_batch(txs: list[TransazioneInput]) -> list[TransazioneScored]:
    semaphore = asyncio.Semaphore(5) #limita a 5 il numero di operazioni che si possono fare contemporaneamente

    async def safe_classify(tx: TransazioneInput):
        async with semaphore: # mette una sorta di semaforo per limitare il numero di operazioni a 5
            return await classifica_singola_transazione(tx)

    tasks = [safe_classify(tx) for tx in txs] #crea una lista di task per classificare ogni transazione in modo sicuro (rispettando il limite del semaforo)

    return await asyncio.gather(*tasks) #attende che tutti i task siano completati e restituisce i risultati in una lista
    # Logica di classificazione fittizia basata sull