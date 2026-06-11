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


class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    source_types: list[str] | None = None
    top_k: int = Field(default=8, ge=1, le=30)
    mode: str = Field(default="balanced", pattern="^(textbook_first|solution_first|balanced|solution_only|textbook_only)$")
    filters: dict | None = None
    intent: str = "general"
    min_similarity: float = Field(DEFAULT_RAG_MIN_SIMILARITY, ge=0.0, le=1.0)


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


class RagSearchResultResponse(BaseModel):
    chunk_id: int
    source_type: str
    score: float
    content: str
    page_start: int | None = None
    page_end: int | None = None
    chapter_title: str | None = None
    lesson_title: str | None = None
    chunk_type: str
    exercise_number: str | None = None
    question_number: str | None = None
    metadata: dict | list | None = None


class RagSearchResponse(BaseModel):
    query: str
    mode: str
    results: list[RagSearchResultResponse]
    diagnostics: dict = Field(default_factory=dict)


class RagAnswerRequest(RagSearchRequest):
    answer_scope: str = Field(default="auto", pattern="^(auto|book_only|tutor_general)$")


class RagAnswerResponse(BaseModel):
    answer: str
    sources: list[RagSearchResultResponse]
    confidence: float
    diagnostics: dict = Field(default_factory=dict)
