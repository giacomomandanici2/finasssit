from pydantic import BaseModel


class RAGResponse(BaseModel):
    answer: str
    citations: list[int]
