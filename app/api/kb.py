from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth import verify_token
from app.core.db import SessionDep
from app.kb.service import KBSearchService


class SearchItem(BaseModel):
    chunk_id: int
    content_preview: str
    document: str
    score: float


router = APIRouter(prefix="/api/v1/kb", tags=["kb"])


@router.get("/search", response_model=list[SearchItem])
async def search_kb(
    db: SessionDep,
    _token: str = Depends(verify_token),
    q: str = Query(..., min_length=1),
    roles: list[str] = Query(default=["public"]),
    k: int = Query(default=10, ge=1, le=100),
) -> list[SearchItem]:
    service = KBSearchService(db)
    results = await service.search(query=q, roles=roles, k=k)
    return [
        SearchItem(
            chunk_id=r.id,
            content_preview=r.content[:200],
            document=r.document_id,
            score=r.score,
        )
        for r in results
    ]
