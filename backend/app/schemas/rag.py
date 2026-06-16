"""Pydantic schemas for retrieval responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


DEFAULT_RAG_MIN_SIMILARITY = 0.45


class RagRetrieveRequest(BaseModel):
    query: str
    unit_id: int | None = None
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
    unit_id: int | None = None
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
    unit_id: int | None = None
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


class RagReembedRequest(BaseModel):
    source_id: int | None = None
    source_type: str | None = None
    batch_size: int = Field(default=50, ge=1, le=500)
    dry_run: bool = False
    force: bool = True
    resume_failed: bool = False


class RagReembedResponse(BaseModel):
    job_id: str
    status: str
    message: str


class RagReembedStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    total_chunks: int = 0
    total_candidates: int = 0
    processed: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    embedding_model: str | None = None
    dry_run: bool = False
    source_id: int | None = None
    source_type: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class RagEvaluationRequest(BaseModel):
    fail_on_threshold: bool = False
    dataset_path: str = "data/eval/rag_gold_questions.json"
    report_dir: str = "data/eval/reports"
    top_k: int = Field(default=5, ge=1, le=20)


class RagEvaluationResponse(BaseModel):
    status: str
    passed: bool
    report_json_path: str
    report_markdown_path: str
    metrics: dict[str, Any]
    threshold_failures: list[str] = Field(default_factory=list)


class RetrievedChunkLogResponse(BaseModel):
    id: int
    rag_query_log_id: int
    chunk_id: int | None = None
    source_id: int | None = None
    source_type: str | None = None
    page_number: int | None = None
    content_type: str | None = None
    rank: int
    similarity_score: float | None = None
    hybrid_score: float | None = None
    rerank_score: float | None = None
    used_in_answer: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RagQueryLogResponse(BaseModel):
    id: int
    user_id: int | None = None
    query_text: str
    normalized_query: str | None = None
    route: str
    source_mode: str | None = None
    top_k: int
    min_similarity: float
    embedding_model: str | None = None
    retrieval_latency_ms: int | None = None
    generation_latency_ms: int | None = None
    total_latency_ms: int | None = None
    result_count: int
    max_similarity: float | None = None
    avg_similarity: float | None = None
    low_confidence: bool
    answer_confidence: float | None = None
    metadata_json: dict | list | None = None
    created_at: datetime
    retrieved_chunks: list[RetrievedChunkLogResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
