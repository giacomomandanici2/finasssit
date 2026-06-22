import logging
import uuid
from contextvars import ContextVar

import jwt
from fastapi import Request
from pythonjsonlogger import jsonlogger

from app.core.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


class ContextLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        rid = request_id_var.get()
        uid = user_id_var.get()
        if rid:
            record.request_id = rid
        if uid:
            record.user_id = uid
        return True


def setup_logging() -> None:
    handler = logging.StreamHandler()
    fmt = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s %(user_id)s",
        timestamp=True,
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(fmt)
    handler.addFilter(ContextLogFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def extract_log_context(request: Request) -> None:
    rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
    request_id_var.set(rid)

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.removeprefix("Bearer ")
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret.get_secret_value(),
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
            user_id_var.set(str(payload.get("sub", "")))
        except jwt.InvalidTokenError:
            pass
