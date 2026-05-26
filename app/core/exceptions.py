

class FinAssistError (Exception):
    """Base class for all exceptions in the FinAssist application."""
    def __init__(self, message: str, code:str="FINASSIST_ERROR"):
        self.code = code
        super().__init__(message) # Chiamare il costruttore della classe base con il messaggio di errore
        
class ValidationErro(FinAssistError):
    """Exception raised for validation errors."""
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")
        
class ClassificationError(FinAssistError):
            def __init__(self, message:str):
                super().__init__(message, code="CLASSIFICATION_ERROR")
                
class UpstreamTimeoutError(FinAssistError):
            def __init__(self, message:str):
                super().__init__(message, code="UPSTREAM_TIMEOUT_ERROR")
                
                