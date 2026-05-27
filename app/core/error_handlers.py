"""Exception handler globali per mappare FinAssistError → HTTP."""
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    ExternalServiceError,
    FinAssistError,
    ResourceNotFoundError,
    TransazioneInvalidaError,
)

logger = logging.getLogger("finassist.errors")


def _error_response(request: Request, exc: FinAssistError, http_status: int) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    payload = {
        "code": exc.status_code,
        "message": str(exc),
    }
    if request_id:
        payload["request_id"] = request_id
    return JSONResponse(status_code=http_status, content=payload)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra tutti gli exception handler su una app FastAPI."""

    @app.exception_handler(TransazioneInvalidaError)
    async def _h_invalid(request: Request, exc: TransazioneInvalidaError) -> JSONResponse:
        logger.warning(
            "Transazione invalida",
            extra={"code": exc.status_code, "transazione_id": exc.transazione_id},
        )
        return _error_response(request, exc, status.HTTP_400_BAD_REQUEST)

    @app.exception_handler(ResourceNotFoundError)
    async def _h_not_found(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
        return _error_response(request, exc, status.HTTP_404_NOT_FOUND)

    @app.exception_handler(ExternalServiceError)
    async def _h_external(request: Request, exc: ExternalServiceError) -> JSONResponse:
        logger.error(
            "Errore servizio esterno",
            extra={"code": exc.status_code, "service": exc.service},
        )
        return _error_response(request, exc, status.HTTP_502_BAD_GATEWAY)

    @app.exception_handler(FinAssistError)
    async def _h_generic(request: Request, exc: FinAssistError) -> JSONResponse:
        # Catch-all per FinAssistError non mappate specificamente
        logger.error("FinAssistError", extra={"code": exc.status_code})
        return _error_response(request, exc, status.HTTP_500_INTERNAL_SERVER_ERROR)