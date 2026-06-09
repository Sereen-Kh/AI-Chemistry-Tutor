"""Pydantic schemas for retrieval responses."""

from pydantic import BaseModel, Field


DEFAULT_RAG_MIN_SIMILARITY = 0.45


class RagRetrieveRequest(BaseModel):
    query: str
    chapter_id: int | None = None
    lesson_id: int | None = None
    topic_id: int | None = None
    source_types: list[str] | None = None
    content_types: list[str] | None = None
    top_k: int = 6
    min_similarity: float = Field(DEFAULT_RAG_MIN_SIMILARITY, ge=0.0, le=1.0)
    intent: str = "general"


class RagRetrieveDebugRequest(RagRetrieveRequest):
    min_similarity: float = Field(0.0, ge=-1.0, le=1.0)


class RagSemanticRetrieveRequest(BaseModel):
    query: str
    chapter_id: int | None = None
    lesson_id: int | None = None
    topic_id: int | None = None
    source_types: list[str] | None = None
    top_k: int = 6
    intent: str = "general"


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


class RagRetrieveResponse(BaseModel):
    chunks: list[RetrievedChunkResponse]


class RagRetrieveDebugResponse(BaseModel):
    chunks: list[RetrievedChunkResponse]
    diagnostics: dict


class RagSemanticRetrieveResponse(BaseModel):
    chunks: list[RetrievedChunkResponse]
    diagnostics: dict
    quality_gate: dict | None = None
