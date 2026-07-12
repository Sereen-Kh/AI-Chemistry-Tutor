"""Pydantic schemas for ingestion endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class IngestionStartRequest(BaseModel):
    pdf_path: str = Field(..., min_length=1)
    title: str | None = None
    source_type: str = "textbook"
    grade: str = "grade_9"
    subject: str = "chemistry"
    year: int | None = None
    max_pages: int | None = Field(default=None, ge=1)
    ocr_provider: str | None = Field(default=None, pattern="^(gemini|gemini_document|gemini_vision)$")
    ingestion_mode: str | None = Field(default=None, pattern="^(production|dry_run)$")
    ocr_required_for_vision: bool | None = None
    allow_partial_ingestion: bool | None = None
    chapter_id: int | None = None
    lesson_id: int | None = None
    topic_id: int | None = None
    clear_existing: bool = False


class IngestionRebuildCacheRequest(BaseModel):
    cache_dir: str = "data/textbooks/syria_grade_9_chemistry/pages"
    title: str = "syria_grade_9_chemistry"
    source_type: str = "textbook"
    grade: str = "grade_9"
    subject: str = "chemistry"
    year: int | None = None
    file_path: str | None = "data/textbooks/syria_grade_9/Chemistry.pdf"
    chapter_id: int | None = None
    lesson_id: int | None = None
    topic_id: int | None = None
    clear_existing: bool = True


class IngestionRebuildCacheResponse(BaseModel):
    source_id: int
    source_title: str
    source_status: str
    cache_dir: str
    total_cache_pages: int
    readable_pages: int
    stored_pages: int
    empty_pages: int
    failed_pages: list[int] = Field(default_factory=list)
    skipped_pages: list[int] = Field(default_factory=list)
    chunks_deleted: int = 0
    questions_deleted: int = 0
    chunks_created: int = 0
    questions_created: int = 0
    content_type_counts: dict[str, int] = Field(default_factory=dict)
    embedding_provider: dict = Field(default_factory=dict)


class SourceRegisterRequest(BaseModel):
    source_type: str
    title: str
    grade: str = "grade_9"
    subject: str = "chemistry"
    year: int | None = None
    file_path: str | None = None
    original_filename: str | None = None
    metadata_json: dict | list | None = None


class SourceResponse(BaseModel):
    id: int
    source_type: str
    title: str
    grade: str
    subject: str
    year: int | None = None
    file_path: str | None = None
    original_filename: str | None = None
    status: str
    metadata_json: dict | list | None = None
    chunk_count: int = 0
    embedded_chunk_count: int = 0
    question_count: int = 0
    pages_summary: dict[str, int] = Field(default_factory=dict)
    canonical_source: bool = False
    file_sha256: str | None = None
    file_size_bytes: int | None = None
    page_count: int | None = None
    reviewed_metadata_version: str | None = None
    reviewed_metadata_status: str | None = None
    ready_for_embedding: bool | None = None
    embedding_status: str | None = None
    missing_metadata_count: int = 0
    manual_review_count: int = 0
    reviewed_chunks_path: str | None = None
    reviewed_preview_path: str | None = None
    reviewed_metadata_path: str | None = None

    model_config = {"from_attributes": True}


class CanonicalSourceStatus(BaseModel):
    source_type: str
    title: str
    file_path: str
    grade: str
    subject: str
    year: int | None = None
    exists: bool
    file_size_bytes: int | None = None
    sha256: str | None = None
    page_count: int | None = None
    source_id: int | None = None
    source_status: str | None = None
    chunk_count: int = 0
    embedded_chunk_count: int = 0
    reviewed_metadata_version: str | None = None
    reviewed_metadata_status: str | None = None
    ready_for_embedding: bool = False
    missing_metadata_count: int = 0
    manual_review_count: int = 0
    embedding_status: str = "not_embedded"
    reviewed_chunks_path: str | None = None
    reviewed_preview_path: str | None = None
    reviewed_metadata_path: str | None = None
    errors: list[str] = Field(default_factory=list)


class CanonicalSourcesValidationResponse(BaseModel):
    sources: list[CanonicalSourceStatus]
    registered_count: int = 0
    updated_count: int = 0
    missing_count: int = 0
    reviewed_metadata_version: str | None = None
    ready_for_embedding: bool = False
    can_prepare_chunks: bool = False


class PrepareReviewedChunksRequest(BaseModel):
    write: bool = True
    include_textbook: bool = True
    include_solution_book: bool = True


class PrepareReviewedChunksResponse(BaseModel):
    status: str
    write: bool
    reviewed_metadata_version: str
    ready_for_embedding: bool
    textbook: dict = Field(default_factory=dict)
    solution_book: dict = Field(default_factory=dict)
    counts: dict = Field(default_factory=dict)
    blocking_issues: list[str] = Field(default_factory=list)
    files_written: list[str] = Field(default_factory=list)
    backups: list[str] = Field(default_factory=list)


class LoadReviewedChunksRequest(BaseModel):
    clear_existing: bool = False
    dry_run: bool = False
    include_textbook: bool = True
    include_solution_book: bool = True


class LoadReviewedChunksResponse(BaseModel):
    status: str
    clear_existing: bool
    dry_run: bool = False
    would_write: bool = False
    reviewed_metadata_version: str | None = None
    sources: dict = Field(default_factory=dict)
    chunks_deleted: int = 0
    chunks_inserted: int = 0
    chunks_updated: int = 0
    chunks_unchanged: int = 0
    chunks_stale: int = 0
    embedding_reset: int = 0
    skipped_blocked: int = 0
    skipped_missing_metadata: int = 0
    skipped_empty_content: int = 0
    embedding_status: str = "pending"
    next_step: str


class EmbeddingReadinessResponse(BaseModel):
    reviewed_metadata_version: str | None = None
    status: str
    ready_for_embedding: bool
    blocking_issues: list[str] = Field(default_factory=list)
    required_chunk_metadata: list[str] = Field(default_factory=list)
    allowed_source_types: list[str] = Field(default_factory=list)
    embedding_model: str
    embedding_dimension: int
    vector_store: str
    vector_index: str
    textbook_chunks_total: int = 0
    textbook_missing_metadata_count: int = 0
    solution_chunks_total: int = 0
    solution_manual_review_count: int = 0
    solution_bad_endings_count: int = 0
    ready_chunk_count: int = 0
    needs_review_chunk_count: int = 0
    blocked_chunk_count: int = 0


class IngestionPageResponse(BaseModel):
    id: int | None = None
    source_id: int
    job_id: int | None = None
    page_number: int
    page_type: str
    status: str
    extraction_methods: list | dict | None = None
    cache_path: str | None = None
    char_count: int = 0
    completeness_score: float = 0.0
    warnings_json: dict | list | None = None
    errors_json: dict | list | None = None
    content_preview: str | None = None

    model_config = {"from_attributes": True}


class IngestionRetryPageResponse(BaseModel):
    page_id: int
    status: str
    message: str
    page: IngestionPageResponse | None = None
    chunks_deleted: int = 0
    questions_deleted: int = 0
    chunks_created: int = 0
    questions_created: int = 0
    cache_invalidation: dict[str, int] = Field(default_factory=dict)


class IngestionTestQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class IngestionTestQueryResponse(BaseModel):
    query: str
    chunks: list[dict]


class IngestionStartResponse(BaseModel):
    task_id: str
    status: str


class SolutionBookIngestRequest(BaseModel):
    file_path: str = "data/textbooks/solution-book/Chemistry_Solution_Book.pdf"
    mode: str = Field(default="dry_run", pattern="^(dry_run|production)$")
    force_reingest: bool = False
    use_ocr: bool = True
    use_vision: bool = True
    allow_partial: bool = False
    max_pages: int | None = Field(default=None, ge=1)
    ocr_provider: str | None = Field(default=None, pattern="^(gemini|gemini_document|gemini_vision|none)$")
    document_id: str = "chemistry_grade9_solution_book"
    title: str = "Chemistry Solution Book - Grade 9"
    output_dir: str = "data/processed/solution_book"


class SolutionBookIngestResponse(BaseModel):
    status: str
    mode: str
    document_id: str
    source_type: str
    source_id: int | None = None
    pdf_path: str
    output_dir: str
    source_file_hash: str
    pages_total: int
    pages_extracted_digitally: int
    pages_needing_ocr: int
    pages_needing_vision: int
    blocked_pages: list[int] = Field(default_factory=list)
    solution_units: int
    chunks: int
    chunks_inserted: int
    chunks_skipped_duplicate: int
    duplicate_chunk_count: int
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    reports: dict[str, str] = Field(default_factory=dict)


class SolutionBookReportResponse(BaseModel):
    report: dict


class IngestionStatusResponse(BaseModel):
    task_id: str
    job_uid: str | None = None
    status: str
    progress: int = 0
    message: str | None = None
    source_id: int | None = None
    source_status: str | None = None
    result: dict | list | None = None
    total_pages: int = 0
    pages_to_process: int = 0
    selectable_text_pages: int = 0
    needs_vision_pages: int = 0
    mixed_vision_pages: int = 0
    chunks_created: int = 0
    questions_extracted: int = 0
    diagrams_extracted: int = 0
    tables_extracted: int = 0
    equations_extracted: int = 0
    pages_processed: int = 0
    pages_completed: int = 0
    pages_failed: int = 0
    pages_skipped_dry_run: int = 0
    ocr_provider: str | None = None
    ocr_provider_configured: bool | None = None
    vision_provider: str | None = None
    vision_provider_configured: bool | None = None
    ingestion_mode: str | None = None
    ocr_required_for_vision: bool | None = None
    allow_partial_ingestion: bool | None = None
    failed_pages: list[int] = Field(default_factory=list)
    skipped_dry_run_pages: list[int] = Field(default_factory=list)
    page_statuses: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    pages: dict[str, int] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IngestionStatsResponse(BaseModel):
    total_chunks: int
    total_sources: int = 0
    total_questions: int = 0
    reviewed_questions: int = 0
    unreviewed_questions: int = 0
    chunks_by_chapter: dict[str, int]
    chunks_by_source_type: dict[str, int] = {}
    avg_chunk_length: float
    pages_processed: int


class IngestionClearResponse(BaseModel):
    deleted_chunks: int


class TestChunkResponse(BaseModel):
    chunk: dict
    similar_chunks: list[dict]


class SourceDeleteResponse(BaseModel):
    deleted_source_id: int
    deleted_chunks: int
    deleted_questions: int


class ExtractedQuestionResponse(BaseModel):
    id: int
    source_id: int
    chapter_id: int | None = None
    lesson_id: int | None = None
    topic_id: int | None = None
    page_number: int | None = None
    question_text: str
    question_type: str
    options: list | dict | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    answer_source: str
    difficulty: int | None = None
    needs_review: bool
    metadata_json: dict | list | None = None

    model_config = {"from_attributes": True}


class QuestionReviewRequest(BaseModel):
    question_text: str | None = None
    question_type: str | None = None
    options: list | dict | None = None
    correct_answer: str | None = None
    explanation: str | None = None
    answer_source: str = "manual"
    difficulty: int | None = None
    needs_review: bool = False
