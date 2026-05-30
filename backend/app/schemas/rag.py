"""Pydantic schemas for retrieval responses."""

from pydantic import BaseModel


class RetrievedChunkResponse(BaseModel):
    id: int
    content: str
    source: str | None = None
    page_number: int | None = None
    chapter_id: int | None = None
    similarity_score: float
