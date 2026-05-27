from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "FinAssist AI"
    scoring_threshold_high: int = 10_000
    scoring_threshold_medium: int = 5_000


@lru_cache
def get_settings() -> Settings:
    return Settings()