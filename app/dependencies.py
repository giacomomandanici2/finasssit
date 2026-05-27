from app.core.config import get_settings
from app.services.scoring_service import ScoringService


def get_scoring_service() -> ScoringService:
    settings = get_settings()
    return ScoringService(settings)