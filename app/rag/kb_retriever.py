import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.kb.service import KBSearchService

logger = logging.getLogger(__name__)

ROLE_ACCESS_MAP: dict[str, list[str]] = {
    "retail": ["public"],
    "compliance": ["public", "compliance_only"],
    "admin": ["public", "compliance_only"],
}


class KBRetriever:
    def __init__(self, db: AsyncSession, user_role: str = "retail") -> None:
        self._search_service = KBSearchService(db)
        self._roles = ROLE_ACCESS_MAP.get(user_role, ["public"])

    async def retrieve(self, query: str, k: int = 5) -> list[dict]:
        results = await self._search_service.search(
            query=query,
            roles=self._roles,
            k=k,
        )
        return [
            {
                "id": r.id,
                "document_id": r.document_id,
                "section": r.section,
                "content": r.content,
                "score": r.score,
            }
            for r in results
        ]
