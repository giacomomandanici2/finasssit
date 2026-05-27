import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

logger = logging.getLogger("finassist.access")


async def request_id_and_access_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()

    response = await call_next(request)
    durata_ms = (time.perf_counter() - start) * 1000
    #aggiungo header di risposta
    response.headers["X-Request-Id"] = request_id
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(durata_ms, 2),
        },
    )
    return response