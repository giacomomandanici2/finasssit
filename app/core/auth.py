from fastapi import Header, HTTPException, status

from app.core.config import settings


async def verify_token(x_api_key: str = Header(...)) -> str:
    if x_api_key != settings.api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API token",
        )
    return x_api_key
