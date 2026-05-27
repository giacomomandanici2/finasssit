class FinAssistError(Exception):
    def __init__(self, message:str, status_code:str ="FINASSIST_ERROR"):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class TransazioneInvalidaError(FinAssistError):
    def __init__(self, motivo:str, transazione_id:str|None = None):
        super().__init__(f"Transazione invalida: {motivo}", status_code = "TRANSAZIONE_INVALIDA")
        self.motivo = motivo
        self.transazione_id = transazione_id        


class ResourceNotFoundError(FinAssistError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} '{identifier}' non trovato", status_code="NOT_FOUND")
        self.resource = resource
        self.identifier = identifier


class ExternalServiceError(FinAssistError):
    def __init__(self, service: str, original: Exception | None = None):
        super().__init__(f"Errore chiamando {service}", status_code="EXTERNAL_SERVICE_ERROR")
        self.service = service
        self.original = original