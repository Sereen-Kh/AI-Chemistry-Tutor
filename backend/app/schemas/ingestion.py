"""Pydantic schemas for ingestion endpoints."""

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

    model_config = {"from_attributes": True}


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


class IngestionTestQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class IngestionTestQueryResponse(BaseModel):
    query: str
    chunks: list[dict]


class IngestionStartResponse(BaseModel):
    task_id: str
    status: str


class IngestionStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    source_id: int | None = None
    source_status: str | None = None
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
