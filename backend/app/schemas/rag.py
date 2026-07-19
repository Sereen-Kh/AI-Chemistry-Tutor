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
    printed_page_start: int | None = None
    printed_page_end: int | None = None
    unit_id: int | str | None = None
    chapter_id: int | None = None
    lesson_id: int | str | None = None
    topic_id: int | None = None
    metadata_json: dict | list | None = None
    quality_status: str | None = None
    quality_warning: str | None = None
    reviewed_metadata_version: str | None = None
    curriculum_metadata: dict[str, Any] | None = None
    similarity_score: float


class RagCitationResponse(BaseModel):
    chunk_id: int
    source_id: int
    source: str | None = None
    source_type: str
    page_number: int | None = None
    printed_page_start: int
    printed_page_end: int
    unit_id: int | str
    lesson_id: int | str
    content_type: str
    content_preview: str | None = None
    quality_status: str
    quality_warning: str | None = None
    reviewed_metadata_version: str
    score: float
    similarity_score: float
    curriculum_metadata: dict[str, Any] = Field(default_factory=dict)


class RagRetrieveResponse(BaseModel):
    chunks: list[RetrievedChunkResponse]
    citations: list[RagCitationResponse] = Field(default_factory=list)


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
    force: bool = False
    resume_failed: bool = False
    resume_after_chunk_id: int | None = Field(default=None, ge=0)
    batch_delay_seconds: float = Field(default=0.0, ge=0, le=300)


class RagReembedResponse(BaseModel):
    job_id: str
    status: str
    message: str


class RagSourceStatusResponse(BaseModel):
    id: str
    db_source_id: int | None = None
    source_type: str
    file_path: str
    filename: str
    checksum_sha256: str | None = None
    page_count: int | None = None
    file_size_bytes: int | None = None
    last_modified_at: str | None = None
    ingestion_status: str
    extraction_status: str
    chunk_status: str
    embedding_status: str
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)


class RagChunkExplorerItemResponse(BaseModel):
    id: int
    source_id: int
    source_type: str
    source_file: str | None = None
    reviewed_chunk_id: int | str | None = None
    content_type: str
    page_number: int | None = None
    unit_id: int | str | None = None
    lesson_id: int | str | None = None
    topic_id: int | None = None
    printed_page_start: int | None = None
    printed_page_end: int | None = None
    quality_status: str | None = None
    reviewed_metadata_version: str | None = None
    embedding_status: str
    embedding_model: str | None = None
    embedding_error: str | None = None
    content_hash: str | None = None
    missing_metadata: list[str] = Field(default_factory=list)
    embedding_allowed: bool = False
    rag_search_allowed: bool = False
    student_generation_allowed: bool = False
    warning_required: bool = False
    reason_codes: list[str] = Field(default_factory=list)
    legacy_unmapped: bool = False
    stale: bool = False
    content_preview: str
    metadata_json: dict | list | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RagChunkExplorerResponse(BaseModel):
    total: int
    filtered_total: int | None = None
    limit: int
    offset: int
    items: list[RagChunkExplorerItemResponse]
    counts: dict[str, int] = Field(default_factory=dict)
    global_counts: dict[str, int] = Field(default_factory=dict)


class RagPreflightDatabaseResponse(BaseModel):
    dialect: str
    reachable: bool
    pgvector_available: bool
    pgvector_version: str | None = None
    embedding_dimension: int
    vector_index_present: bool
    vector_index_name: str | None = None
    vector_index_type: str | None = None
    distance_operator: str | None = None
    vector_column_type: str | None = None
    vector_dimension_valid: bool = False


class RagPreflightProviderResponse(BaseModel):
    provider: str
    model: str
    configured: bool


class RagPreflightReviewedMetadataResponse(BaseModel):
    exists: bool
    status: str
    version: str | None = None
    ready_for_embedding: bool
    blocking_issues: list[str] = Field(default_factory=list)


class RagPreflightSourcesResponse(BaseModel):
    textbook_found: bool
    solution_book_found: bool
    reviewed_textbook_chunks_found: bool
    reviewed_solution_chunks_found: bool


class RagPreflightChunkCountsResponse(BaseModel):
    reviewed_chunks_total: int = 0
    database_chunks_total: int = 0
    ready_chunks: int = 0
    needs_review_chunks: int = 0
    blocked_chunks: int = 0
    missing_metadata_chunks: int = 0
    pending_embeddings: int = 0
    processing_embeddings: int = 0
    completed_embeddings: int = 0
    failed_embeddings: int = 0
    wrong_dimension_embeddings: int = 0
    completed_vectors_missing: int = 0
    noncompleted_with_embeddings: int = 0
    embedding_model_mismatch: int = 0
    stale_chunks: int = 0


class RagPreflightResponse(BaseModel):
    status: str = Field(pattern="^(ready|blocked|degraded)$")
    database: RagPreflightDatabaseResponse
    provider: RagPreflightProviderResponse
    reviewed_metadata: RagPreflightReviewedMetadataResponse
    sources: RagPreflightSourcesResponse
    chunks: RagPreflightChunkCountsResponse
    can_load_chunks: bool
    can_embed: bool
    can_evaluate: bool
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


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
    reviewed_metadata_version: str | None = None
    metadata_ready: bool = False
    skipped_missing_metadata_count: int = 0
    skipped_blocked_count: int = 0
    skipped_stale_count: int = 0
    dry_run: bool = False
    source_id: int | None = None
    source_type: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


class RagEvaluationRequest(BaseModel):
    fail_on_threshold: bool = False
    confirm_live_provider_calls: bool = False
    dataset_path: str = "data/eval/rag_gold_questions.json"
    report_dir: str = "data/eval/reports"
    top_k: int = Field(default=5, ge=1, le=20)


class RagEvaluationResponse(BaseModel):
    status: str
    passed: bool
    reviewed_metadata_version: str | None = None
    embedding_model: str | None = None
    preconditions: dict[str, Any] = Field(default_factory=dict)
    report_json_path: str
    report_markdown_path: str
    metrics: dict[str, Any]
    threshold_failures: list[str] = Field(default_factory=list)
    failed_cases: list[dict[str, Any]] = Field(default_factory=list)


class RagQaRequest(BaseModel):
    mode: str = Field(default="unit", pattern="^(unit|integration)$")


class RagQaResponse(BaseModel):
    status: str
    reviewed_metadata_version: str | None = None
    embedding_model: str | None = None
    preconditions: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    threshold_failures: list[str] = Field(default_factory=list)
    failed_cases: list[dict[str, Any]] = Field(default_factory=list)
    report_json_path: str
    report_markdown_path: str | None = None


class RagOperationsResponse(BaseModel):
    status: str
    window_hours: int
    last_updated_at: datetime
    active_reviewed_metadata_version: str | None = None
    embedding_model: str
    student_retrieval_enabled: bool
    production_gate_required: bool
    production_gate_status: dict[str, Any] = Field(default_factory=dict)
    preflight_status: str
    total_eligible_chunks: int = 0
    embedded_eligible_chunks: int = 0
    embedding_completion_rate: float = 0.0
    ready_chunks: int = 0
    needs_review_chunks: int = 0
    blocked_chunks: int = 0
    stale_chunks: int = 0
    query_volume: int = 0
    no_result_rate: float = 0.0
    low_confidence_rate: float = 0.0
    average_retrieval_latency_ms: float = 0.0
    p95_retrieval_latency_ms: float = 0.0
    source_type_distribution: dict[str, int] = Field(default_factory=dict)
    quality_status_counts: dict[str, int] = Field(default_factory=dict)
    missing_citation_metadata_count: int = 0
    latest_embedding_job: dict[str, Any] | None = None
    latest_evaluation: dict[str, Any] | None = None
    latest_student_flow_qa: dict[str, Any] | None = None
    degraded_reasons: list[str] = Field(default_factory=list)


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
