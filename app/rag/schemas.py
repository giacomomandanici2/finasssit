from pydantic import BaseModel


class RAGResponse(BaseModel):
    answer: str
    citations: list[int]


class RAGAnswerRequest(BaseModel):
    query: str
    session_id: int | None = None


class CitationItem(BaseModel):
    id: int
    document: str
    section: str


class RAGAnswerResponse(BaseModel):
    answer: str
    citations: list[CitationItem]
    request_id: str
