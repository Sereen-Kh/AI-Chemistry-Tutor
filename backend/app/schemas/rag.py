"""Pydantic schemas for retrieval responses."""

from pydantic import BaseModel


class RetrievedChunkResponse(BaseModel):
    id: int
    source_id: int
    content: str
    source: str | None = None
    source_type: str
    content_type: str
    page_number: int | None = None
    chapter_id: int | None = None
    lesson_id: int | None = None
    topic_id: int | None = None
    metadata_json: dict | list | None = None
    similarity_score: float
