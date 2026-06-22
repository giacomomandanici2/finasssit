import logging

import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_user_id_from_jwt(request: Request) -> str:
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
            return f"user_{payload['sub']}"
        except jwt.InvalidTokenError:
            logger.debug("Invalid token for rate limit key, falling back to IP")
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_user_id_from_jwt,
    default_limits=["60/minute"],
)
