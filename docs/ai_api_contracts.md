# EduMind AI API Contracts And Backend Gap Report

Date: 2026-06-05

Scope: backend AI APIs for ingestion, Gemini document extraction, embeddings, pgvector RAG, chatbot, quizzes, homework, flashcards, and admin review. This document is based on the current backend code, not a desired-only design.

## Architecture Decisions

- Production vector store: PostgreSQL with pgvector, `VECTOR(768)`.
- Production OCR/document provider: Gemini through the `google-genai` SDK.
- Primary extraction path: upload the PDF once, then extract target pages directly from the uploaded PDF.
- Fallback extraction path: render the page image at 300 DPI only when direct PDF extraction fails or quality is poor.
- Production must not use Qdrant.
- Production must not use OCRArena. Existing OCRArena references are only benchmark/debug references.
- Production must not use legacy `google-generativeai`.
- Long-running ingestion should run through Celery, not FastAPI in-process background tasks.
- All public backend APIs should appear in Swagger under `/docs`, use Pydantic schemas, and call service-layer functions.
- Admin ingestion and review APIs must be protected.
- AI generated questions/answers must be marked as generated or review-required unless approved by an admin.

## Phase 0 Gap Report

### 1. Existing AI-Related Files

- API routers: `backend/app/api/ingestion/routes.py`, `backend/app/api/rag/routes.py`, `backend/app/api/chat/routes.py`, `backend/app/api/quizzes.py`, `backend/app/api/exams.py`, `backend/app/api/homework.py`, `backend/app/api/flashcards.py`, `backend/app/api/health.py`.
- Schemas: `backend/app/schemas/ingestion.py`, `backend/app/schemas/rag.py`, `backend/app/schemas/chat.py`, `backend/app/schemas/quiz.py`, `backend/app/schemas/homework.py`, `backend/app/schemas/flashcards.py`, `backend/app/schemas/common.py`, `backend/app/schemas/extraction.py`.
- Services: `backend/app/services/ingestion_pipeline.py`, `backend/app/services/pdf_processor.py`, `backend/app/services/chunking.py`, `backend/app/services/embeddings.py`, `backend/app/services/rag.py`, `backend/app/services/chat_service.py`, `backend/app/services/ai_service.py`, `backend/app/services/homework_service.py`, `backend/app/services/quiz_service.py`, `backend/app/services/ai_quiz_generator.py`, `backend/app/services/ai_flashcard_generator.py`, `backend/app/services/gemini_client.py`.
- OCR services: `backend/app/services/ocr/base.py`, `backend/app/services/ocr/gemini_provider.py`, `backend/app/services/ocr/quality.py`.
- Workers: `backend/app/workers/celery_app.py`, `backend/app/workers/ingestion_tasks.py`.
- Models: `content_sources`, `rag_chunks`, `extracted_questions`, `ingestion_jobs`, `ingestion_pages`, `chat_sessions`, `chat_messages`, `homework`, `questions`, `quiz_attempts`, `question_attempts`, `flashcards`, `flashcard_progress`, plus user/profile/progress/curriculum models.

### 2. Existing API Routers

Included by `backend/app/api/router.py` under `/api/v1`:

- `auth`, `users`, `student_profile`
- `chapters`, `lessons`, `topics`, `elements`, `study_plans`
- `chat`, `rag`, `admin-ingestion`
- `quizzes`, `exams`, `homework`, `progress`, `flashcards`, `health`

### 3. Routers Missing From `app/main.py`

No existing router file appears to be missing from `app/main.py`.

Missing desired AI router/endpoint coverage:

- AI health/config readiness endpoint.
- Admin single-page extraction smoke test endpoint.
- AI flashcard generation endpoint.

### 4. Existing Pydantic Schemas

Existing schemas cover most current routes:

- Auth/user/profile/curriculum: present.
- Ingestion: present for source registration, start, status, stats, pages, retry, test query, question review.
- RAG: present for basic retrieval.
- Chat: present for sessions, ask, message feedback, answer blocks, sources.
- Quiz/exam: present for generate, submit, history, recommendations.
- Homework: present for solve-text and solve-image.
- Flashcards: present for manual create/review.
- Common health/error: present.

### 5. Missing Pydantic Schemas

- `AIHealthConfigResponse` and provider readiness schema.
- `IngestionTestPageExtractionRequest` and `IngestionTestPageExtractionResponse`.
- `FlashcardGenerateRequest` and `FlashcardGenerateResponse`.
- Upload-based homework image schema. Current `HomeworkSolveImageRequest` accepts `image_path`; mobile will usually need multipart upload or pre-signed upload metadata.
- Richer `RagRetrieveRequest` fields for mobile intent/routing, such as `intent`, `answer_scope`, `include_sources`, `include_snippets`, `filters`.

### 6. Existing Database Models

Important implemented tables:

- Auth/profile: `users`, `student_profiles`, `interest_categories`, `user_interests`.
- Curriculum/progress: `chapters`, `lessons`, `topics`, `lesson_progress`, `user_progress`, `achievements`.
- RAG/ingestion: `content_sources`, `rag_chunks`, `extracted_questions`, `ingestion_jobs`, `ingestion_pages`, legacy `textbook_chunks`.
- Chat: `chat_sessions`, `chat_messages`.
- Quiz/exam: `questions`, `quiz_attempts`, `question_attempts`.
- Homework: `homework`.
- Flashcards: `flashcards`, `flashcard_progress`.
- Supporting: `study_plans`, `device_tokens`, `subscriptions`, `reels`.

### 7. Missing Database Models

No core table from the current AI scope is completely absent, but these model fields are still missing or incomplete:

- `rag_chunks` lacks explicit embedding model/version fields.
- `rag_chunks` lacks approved/unapproved state for generated content.
- `chat_messages` lacks persisted source citations/diagnostics payload.
- `homework` has `source_chunks`, but current service does not fill it.
- Ingestion job status is persisted but API status currently reads in-memory `_TASKS`, so process restarts lose visible progress.
- No dedicated AI provider call audit table for quota, latency, model, and failure analysis.

### 8. Existing Alembic Migrations

- One migration exists: `backend/alembic/versions/0001_initial_schema.py`.
- It enables `vector` on PostgreSQL and calls `Base.metadata.create_all()`.

### 9. Missing Migrations

- Production migration chain should use explicit Alembic operations instead of one metadata `create_all()` migration.
- If adding AI health tables, provider call audit, richer chat citations, generated flashcard status, or embedding metadata, new migrations are required.

### 10. Existing Service-Layer Functions

- Gemini client/config: `get_gemini_client`, `document_generation_config`, `tutor_generation_config`, `embedding_config`.
- OCR/document extraction: `GeminiVisionProvider.upload_pdf`, `extract_page_from_pdf`, `extract_page`, `extract_pdf_page`, `extract_page_image_fallback`.
- PDF processing: `classify_pages`, `extract_selectable_text_page`, `render_page_to_image`.
- Ingestion: `run_full_ingestion`, `_extract_page`, chunk creation, embedding storage.
- Embeddings: `embed_text`, `embed_query`, `embed_batch`.
- RAG: `retrieve_context`, `format_context`.
- Chat: `create_session`, `get_user_sessions`, `get_owned_session`, `send_message`, `ask_question`, `update_message_feedback`, `delete_session`.
- Homework: `solve_text`, `solve_image`.
- Quiz: `generate_quiz`, `submit_quiz`, `list_attempts`, `recommendations`.
- AI generation helpers: `ai_quiz_generator.generate_questions_for_topic`, `ai_flashcard_generator.generate_flashcards_for_topic`.

### 11. Missing Service-Layer Functions

- `ai_health_service.get_ai_config_status`.
- `ingestion_service.start_celery_ingestion` and `ingestion_service.get_job_status` backed by DB/Celery, not `_TASKS`.
- `ingestion_service.test_page_extraction` for one page without mutating source state.
- `flashcard_service.generate_ai_flashcards` wrapping `ai_flashcard_generator`.
- Upload/image-storage service for homework photo submissions.
- RAG cache service using Redis for query result caching.

### 12. Existing Celery Workers

- `backend/app/workers/celery_app.py` configures Celery with Redis.
- `backend/app/workers/ingestion_tasks.py` defines `ingest_pdf_task`.

### 13. Missing Celery Workers

- `POST /admin/ingestion/start` currently uses FastAPI `BackgroundTasks` and an in-memory `_TASKS` map. It should enqueue `ingest_pdf_task`.
- Missing Celery task for per-page retry.
- Missing Celery task for expensive generated flashcards/question generation if those are run async.

### 14. Existing Redis Integration

- `backend/app/core/redis.py` provides a Redis client/pool.
- Docker Compose includes Redis for broker/cache.

### 15. Missing Redis Integration

- RAG retrieval results are not cached.
- Ingestion progress is not cached or recovered from Redis/Celery result backend in the API.
- Rate limiting middleware exists, but AI-specific quota/rate control is not clearly connected to Redis.

### 16. Existing Gemini / `google-genai` Integration

- Backend app code uses `from google import genai` and `google.genai.types`.
- Structured JSON output is implemented for page extraction through `response_mime_type="application/json"` and `response_schema=PageExtractionResult`.
- PDF upload through Gemini Files API exists.
- Direct PDF page extraction exists.
- Rendered image fallback exists.
- Document/query embedding calls exist with `RETRIEVAL_DOCUMENT` and `RETRIEVAL_QUERY`.

### 17. Legacy `google-generativeai` Usage To Remove

- No active usage was found in `backend/app`, `backend/scripts`, or `backend/requirements.txt`.
- Old prompt/docs contain historical `google.generativeai` examples. They should not drive implementation.
- `backend/tests/test_extraction_contract.py` guards against importing legacy `google.generativeai`.

### 18. Qdrant Usage To Avoid

- No production backend app usage found.
- Old docs/handoff files mention Qdrant and OCRArena. Those are historical and should not be used for production.

### 19. Swagger/OpenAPI Readiness Gaps

- Most current routes appear in Swagger and use response models.
- Admin ingestion routes use sync DB sessions, not async DB access.
- Admin ingestion routes are protected by `require_admin`, but `require_admin` is permissive when neither `ADMIN_TOKEN` nor `ADMIN_EMAILS` is configured. Production admin endpoints should use `require_configured_admin`.
- Missing Swagger endpoint for AI provider health/config.
- Missing Swagger endpoint for single page extraction test.
- Missing Swagger endpoint for AI-generated flashcards.
- `POST /homework/solve-image` is not mobile-ready because it accepts `image_path` instead of a file upload or uploaded asset reference.

### 20. Exact Implementation Order

1. Update settings defaults to target model names and add AI health/config response schemas.
2. Add `GET /api/v1/health/ai-config` or `GET /api/v1/ai/health`.
3. Move admin ingestion start/status to a service that dispatches Celery and reads durable DB/Celery status.
4. Add `POST /api/v1/admin/ingestion/test-page-extraction`.
5. Add per-page retry Celery task and wire `POST /api/v1/admin/ingestion/retry-page/{page_id}`.
6. Harden admin dependencies with `require_configured_admin` for production AI admin routes.
7. Add Redis-backed RAG cache.
8. Add richer RAG request/response metadata for mobile.
9. Persist chat citations/diagnostics in `chat_messages` or a related table.
10. Add mobile-ready homework image upload flow.
11. Wire AI flashcard generation route.
12. Add tests for each route contract and Celery dispatch behavior.

## Current Extraction Cache State

Local cache path inspected: `data/textbooks/syria_grade_9_chemistry/pages`.

- Page JSON files: 96.
- Completed text-only pages: 26.
- Completed image-fallback pages: 14.
- Failed or empty pages: 56.
- Most failures are `NEEDS_VISION` or `MIXED_VISION` pages with empty content and Gemini quota/model/invalid-schema errors.

Conclusion: the cache count is complete, but production ingestion is not complete. A source should not be marked `completed` until all required scanned/mixed pages have valid content and pass quality thresholds.

## AI API Execution Order

The APIs are listed in the order they should be used by the system.

### API Order 1 - Admin Source Registration

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/admin/ingestion/sources`

Purpose:
- Register a textbook, exam, answer key, or other source before ingestion.

Called by:
- Admin dashboard, Swagger, future mobile/admin app.

Calls:
- `register_source` route logic.

Database tables:
- `content_sources`

Request:

```json
{
  "source_type": "textbook",
  "title": "Grade 9 Chemistry",
  "grade": "grade_9",
  "subject": "chemistry",
  "year": 2026,
  "file_path": "data/textbooks/syria_grade_9_chemistry/book.pdf",
  "original_filename": "chemistry.pdf",
  "metadata_json": {}
}
```

Response:

```json
{
  "id": 1,
  "source_type": "textbook",
  "title": "Grade 9 Chemistry",
  "grade": "grade_9",
  "subject": "chemistry",
  "year": 2026,
  "file_path": "data/textbooks/syria_grade_9_chemistry/book.pdf",
  "original_filename": "chemistry.pdf",
  "status": "pending",
  "metadata_json": {}
}
```

Error responses:
- `401` invalid bearer token.
- `403` admin privileges required.
- `422` invalid payload.

Service function called:
- Missing dedicated service. Current business logic is inside route.

Status:
- Partial.

Files:
- Existing: `backend/app/api/ingestion/routes.py`, `backend/app/schemas/ingestion.py`, `backend/app/models/textbook.py`.
- Modify later: move logic into `backend/app/services/ingestion_service.py`.

### API Order 2 - Admin Ingestion Start

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/admin/ingestion/start`

Purpose:
- Start full document ingestion: classify pages, extract text/OCR, chunk, embed, and store in pgvector.

Called by:
- Admin Swagger/dashboard after source registration.

Calls:
- Current: `_run_ingestion_task` via FastAPI `BackgroundTasks`.
- Target: Celery `ingest_pdf_task.delay(...)`.

Database tables:
- `ingestion_jobs`, `ingestion_pages`, `content_sources`, `rag_chunks`, `extracted_questions`

Request:

```json
{
  "pdf_path": "data/textbooks/syria_grade_9_chemistry/book.pdf",
  "title": "Grade 9 Chemistry",
  "source_type": "textbook",
  "grade": "grade_9",
  "subject": "chemistry",
  "year": 2026,
  "max_pages": null,
  "ocr_provider": "gemini",
  "ingestion_mode": "production",
  "ocr_required_for_vision": true,
  "allow_partial_ingestion": false,
  "chapter_id": null,
  "lesson_id": null,
  "topic_id": null,
  "clear_existing": false
}
```

Response:

```json
{
  "task_id": "job_uid",
  "status": "queued"
}
```

Error responses:
- `401` invalid bearer token.
- `403` admin privileges required.
- `404` PDF path not found.
- `409` source already being ingested.
- `422` invalid ingestion mode/provider.
- `503` Gemini required but not configured in production mode.

Service function called:
- Current: `run_full_ingestion`.
- Missing target wrapper: `ingestion_service.start_celery_ingestion`.

Status:
- Partial. The pipeline exists, but route uses in-process background tasks and sync DB access.

Files:
- Existing: `backend/app/api/ingestion/routes.py`, `backend/app/services/ingestion_pipeline.py`, `backend/app/workers/ingestion_tasks.py`.
- Modify later: `backend/app/api/ingestion/routes.py`, `backend/app/services/ingestion_service.py`, `backend/app/workers/ingestion_tasks.py`.

### API Order 3 - Gemini PDF Upload

Type:
- External Provider API

Purpose:
- Upload the full PDF once to Gemini Files API so every target page can be extracted directly from the uploaded document.

Called by:
- `run_full_ingestion` through `GeminiVisionProvider.upload_pdf`.

Calls:
- `client.files.upload(...)`
- `client.files.get(...)` while waiting for ACTIVE state.

Database tables:
- None directly. Upload metadata is saved inside source/job/page payloads when ingestion succeeds.

Request:

```json
{
  "pdf_path": "data/textbooks/syria_grade_9_chemistry/book.pdf",
  "mime_type": "application/pdf",
  "display_name": "book.pdf"
}
```

Response:

```json
{
  "provider": "gemini_document",
  "name": "files/abc",
  "uri": "https://generativelanguage.googleapis.com/...",
  "mime_type": "application/pdf",
  "display_name": "book.pdf"
}
```

Error responses:
- Missing API key.
- File not found.
- Gemini file upload failed.
- Gemini file did not become ACTIVE before timeout.

Service function called:
- `GeminiVisionProvider.upload_pdf`
- Alias: `GeminiDocumentProvider.prepare_document`

Status:
- Existing.

Files:
- Existing: `backend/app/services/ocr/gemini_provider.py`, `backend/app/services/ocr/base.py`, `backend/app/services/gemini_client.py`.

### API Order 4 - Gemini Direct PDF Page Extraction

Type:
- External Provider API

Purpose:
- Extract one target page directly from the uploaded PDF with structured JSON output.

Called by:
- Ingestion pipeline for `NEEDS_VISION` and `MIXED_VISION` pages.

Calls:
- `client.models.generate_content(...)` with `response_mime_type="application/json"` and `response_schema=PageExtractionResult`.

Database tables:
- None directly. Result is cached as page JSON and later stored into `rag_chunks`, `extracted_questions`, and `ingestion_pages`.

Request:

```json
{
  "uploaded_pdf": {
    "name": "files/abc",
    "uri": "gemini-file-uri",
    "mime_type": "application/pdf"
  },
  "page_number": 11,
  "source_type": "textbook",
  "neighboring_pages": [10, 12]
}
```

Response:

```json
{
  "page_number": 11,
  "detected_language": "ar",
  "raw_markdown": "Arabic page content...",
  "sections": [],
  "questions": [],
  "diagrams": [],
  "tables": [],
  "equations": [],
  "warnings": [],
  "provider": "gemini_document_pdf",
  "model_name": "gemini-3.5-flash",
  "schema_valid": true,
  "char_count": 1200,
  "completeness_score": 0.9
}
```

Error responses:
- Missing Gemini key.
- Direct PDF extraction disabled.
- Invalid schema.
- Empty sections/raw content.
- Low `char_count`.
- Low `completeness_score`.
- Quota/rate limit.
- Provider timeout.

Service function called:
- `GeminiVisionProvider.extract_page_from_pdf`
- Alias: `GeminiDocumentProvider.extract_pdf_page`

Status:
- Existing, but model config defaults do not match the target architecture.

Files:
- Existing: `backend/app/services/ocr/gemini_provider.py`, `backend/app/services/ocr/quality.py`, `backend/app/core/config.py`.
- Modify later: `backend/app/core/config.py`.

### API Order 5 - Gemini Rendered Image Fallback Extraction

Type:
- External Provider API

Purpose:
- Extract one page from a 300 DPI rendered page image only when direct PDF extraction fails or quality is poor.

Called by:
- Ingestion pipeline fallback.
- Homework image solver.

Calls:
- `render_page_to_image(...)`
- `client.models.generate_content(...)` with image bytes and structured JSON schema.

Database tables:
- None directly for provider call.
- Ingestion result affects `ingestion_pages`, `rag_chunks`, `extracted_questions`.
- Homework result affects `homework`.

Request:

```json
{
  "image_path": "data/textbooks/syria_grade_9_chemistry/pages/img/page_011.png",
  "page_number": 11,
  "source_type": "textbook"
}
```

Response:

```json
{
  "page_number": 11,
  "raw_markdown": "Arabic page content...",
  "sections": [],
  "questions": [],
  "diagrams": [],
  "tables": [],
  "equations": [],
  "warnings": [],
  "provider": "gemini_document_image",
  "model_name": "gemini-2.5-pro",
  "schema_valid": true,
  "char_count": 900,
  "completeness_score": 0.8
}
```

Error responses:
- Missing Gemini key.
- Image path missing.
- Image fallback disabled.
- Invalid schema.
- Empty/low-quality output.
- Quota/rate limit.

Service function called:
- `GeminiVisionProvider.extract_page`
- Alias: `GeminiDocumentProvider.extract_page_image_fallback`

Status:
- Existing.

Files:
- Existing: `backend/app/services/pdf_processor.py`, `backend/app/services/ocr/gemini_provider.py`, `backend/app/services/homework_service.py`.

### API Order 6 - Gemini Document Embeddings

Type:
- External Provider API

Purpose:
- Convert each final RAG chunk into a `VECTOR(768)` document embedding.

Called by:
- Ingestion pipeline after chunking.

Calls:
- `client.models.embed_content(...)` with `task_type="RETRIEVAL_DOCUMENT"`.

Database tables:
- `rag_chunks.embedding`

Request:

```json
{
  "model": "text-embedding-004",
  "contents": ["chunk text 1", "chunk text 2"],
  "task_type": "RETRIEVAL_DOCUMENT",
  "output_dimensionality": 768
}
```

Response:

```json
{
  "embeddings": [
    [0.01, -0.02, 0.03]
  ]
}
```

Error responses:
- Missing Gemini key.
- Model unavailable for selected endpoint/project.
- Empty vector response.
- Quota/rate limit.

Service function called:
- `embed_batch`
- `embed_text`

Status:
- Partial. Calls exist, but current settings default is `gemini-embedding-001`, while target architecture says `text-embedding-004`. Code falls back to deterministic local embeddings on failure, which is useful for dev but not acceptable as a production success condition.

Files:
- Existing: `backend/app/services/embeddings.py`, `backend/app/services/gemini_client.py`, `backend/app/core/config.py`, `backend/app/models/textbook.py`.
- Modify later: `backend/app/core/config.py`, ingestion completion rules.

### API Order 7 - Gemini Query Embeddings

Type:
- External Provider API

Purpose:
- Convert a user query into a `VECTOR(768)` query embedding for pgvector search.

Called by:
- RAG retrieval service.
- Chat service through RAG retrieval.
- Admin ingestion test query.

Calls:
- `client.models.embed_content(...)` with `task_type="RETRIEVAL_QUERY"`.

Database tables:
- Reads `rag_chunks`.

Request:

```json
{
  "model": "text-embedding-004",
  "contents": "ما هي الحموض؟",
  "task_type": "RETRIEVAL_QUERY",
  "output_dimensionality": 768
}
```

Response:

```json
{
  "embedding": [0.01, -0.02, 0.03]
}
```

Error responses:
- Missing Gemini key.
- Model unavailable.
- Empty vector response.
- Quota/rate limit.

Service function called:
- `embed_query`

Status:
- Partial for the same model/default/fallback reason as document embeddings.

Files:
- Existing: `backend/app/services/embeddings.py`, `backend/app/services/rag.py`.
- Modify later: `backend/app/core/config.py`, `backend/app/services/rag.py`.

### API Order 8 - Admin Ingestion Status

Type:
- Internal FastAPI Swagger API

Endpoint:
- `GET /api/v1/admin/ingestion/status/{task_id}`

Purpose:
- Return job progress and page/chunk/question counts.

Called by:
- Swagger, admin dashboard, future mobile/admin app polling.

Calls:
- Current: in-memory `_TASKS`.
- Target: DB `ingestion_jobs` plus Celery result backend.

Database tables:
- Current route does not read DB for status.
- Target: `ingestion_jobs`, `ingestion_pages`.

Request:

```json
{
  "task_id": "job_uid"
}
```

Response:

```json
{
  "task_id": "job_uid",
  "status": "processing",
  "progress": 50,
  "source_id": 1,
  "pages_processed": 48,
  "pages_completed": 40,
  "pages_failed": 8,
  "failed_pages": [23, 24],
  "warnings": [],
  "errors": []
}
```

Error responses:
- `401`, `403`, `404`.

Service function called:
- Missing durable service.

Status:
- Partial.

Files:
- Existing: `backend/app/api/ingestion/routes.py`, `backend/app/schemas/ingestion.py`, `backend/app/models/ingestion.py`.
- Modify later: `backend/app/services/ingestion_service.py`, `backend/app/workers/ingestion_tasks.py`.

### API Order 9 - Admin Source Pages

Type:
- Internal FastAPI Swagger API

Endpoint:
- `GET /api/v1/admin/ingestion/pages/{source_id}`

Purpose:
- List per-page extraction state, quality score, cache path, and errors.

Called by:
- Admin QA screen and Swagger.

Calls:
- Direct DB query.

Database tables:
- `ingestion_pages`

Request:

```json
{
  "source_id": 1
}
```

Response:

```json
[
  {
    "id": 10,
    "source_id": 1,
    "job_id": 1,
    "page_number": 11,
    "page_type": "MIXED_VISION",
    "status": "completed_with_vision",
    "extraction_methods": ["pdf_text", "gemini_pdf_file"],
    "cache_path": "data/textbooks/.../page_011.json",
    "char_count": 1200,
    "completeness_score": 0.9,
    "warnings_json": [],
    "errors_json": [],
    "content_preview": "..."
  }
]
```

Error responses:
- `401`, `403`, `404`.

Service function called:
- Missing dedicated service.

Status:
- Partial. Route exists, but uses sync DB and depends on ingestion writing page rows.

Files:
- Existing: `backend/app/api/ingestion/routes.py`, `backend/app/schemas/ingestion.py`, `backend/app/models/ingestion.py`.

### API Order 10 - Admin Test Page Extraction

Type:
- Internal FastAPI Swagger API

Endpoint:
- Proposed: `POST /api/v1/admin/ingestion/test-page-extraction`

Purpose:
- Smoke test extraction for one page without marking the source completed and without rebuilding all chunks.

Called by:
- Admin Swagger before a full expensive ingestion run.

Calls:
- `classify_pages`
- `upload_pdf` if needed
- `extract_page_from_pdf`
- image fallback on quality failure

Database tables:
- Optional read from `content_sources`.
- Should not write `rag_chunks` unless explicitly requested.

Request:

```json
{
  "pdf_path": "data/textbooks/syria_grade_9_chemistry/book.pdf",
  "page_number": 11,
  "source_type": "textbook",
  "ocr_provider": "gemini",
  "force_image_fallback": false
}
```

Response:

```json
{
  "page_number": 11,
  "page_type": "MIXED_VISION",
  "status": "completed_with_vision",
  "provider": "gemini_document_pdf",
  "model_name": "gemini-3.5-flash",
  "char_count": 1200,
  "completeness_score": 0.9,
  "sections": [],
  "questions": [],
  "tables": [],
  "diagrams": [],
  "equations": [],
  "warnings": [],
  "errors": []
}
```

Error responses:
- `401`, `403`, `404`, `422`, `503`.

Service function called:
- Missing: `ingestion_service.test_page_extraction`.

Status:
- Missing.

Files:
- Create/modify: `backend/app/schemas/ingestion.py`, `backend/app/services/ingestion_service.py`, `backend/app/api/ingestion/routes.py`, tests.

### API Order 11 - Admin Ingestion Stats

Type:
- Internal FastAPI Swagger API

Endpoint:
- `GET /api/v1/admin/ingestion/stats`

Purpose:
- Show total chunks, sources, questions, review count, chunk distribution, and pages processed.

Called by:
- Admin dashboard and Swagger.

Calls:
- Direct DB aggregate queries.

Database tables:
- `content_sources`, `rag_chunks`, `extracted_questions`

Request:

```json
{}
```

Response:

```json
{
  "total_chunks": 120,
  "total_sources": 1,
  "total_questions": 30,
  "reviewed_questions": 10,
  "unreviewed_questions": 20,
  "chunks_by_chapter": {"none": 120},
  "chunks_by_source_type": {"textbook": 120},
  "avg_chunk_length": 650.5,
  "pages_processed": 40
}
```

Error responses:
- `401`, `403`.

Service function called:
- Missing dedicated service.

Status:
- Partial.

Files:
- Existing: `backend/app/api/ingestion/routes.py`, `backend/app/schemas/ingestion.py`.

### API Order 12 - RAG Retrieve

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/rag/retrieve`

Purpose:
- Retrieve source-grounded chunks for a user query with page citations.

Called by:
- Mobile app for source preview.
- Chat service internally.
- Admin test query endpoint.

Calls:
- `retrieve_context`
- `embed_query`
- pgvector similarity search plus lexical reranking.

Database tables:
- `rag_chunks`, `content_sources`

Request:

```json
{
  "query": "ما هي الحموض؟",
  "chapter_id": null,
  "lesson_id": null,
  "topic_id": null,
  "source_types": ["textbook"],
  "content_types": ["text", "table", "diagram", "exercise"],
  "top_k": 6,
  "min_similarity": 0.0
}
```

Response:

```json
{
  "chunks": [
    {
      "id": 13,
      "source_id": 1,
      "content": "الحموض: مواد تعطي...",
      "source": "Grade 9 Chemistry",
      "source_type": "textbook",
      "content_type": "text",
      "page_number": 11,
      "chapter_id": null,
      "lesson_id": null,
      "topic_id": null,
      "metadata_json": {},
      "similarity_score": 0.82
    }
  ]
}
```

Error responses:
- `401` invalid bearer token.
- `422` invalid query/filter values.
- `503` database/vector search unavailable.

Service function called:
- `retrieve_context`

Status:
- Existing, mobile contract should be expanded.

Files:
- Existing: `backend/app/api/rag/routes.py`, `backend/app/schemas/rag.py`, `backend/app/services/rag.py`, `backend/app/services/embeddings.py`.
- Modify later: richer schema and Redis cache.

### API Order 13 - Chat Session Creation

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/chat/sessions`

Purpose:
- Create a persistent tutoring chat session.

Called by:
- Mobile app when opening a new chat.

Calls:
- `chat_service.create_session`

Database tables:
- `chat_sessions`

Request:

```json
{
  "title": "Acids lesson",
  "lesson_id": null,
  "style": "simple"
}
```

Response:

```json
{
  "id": 1,
  "user_id": 1,
  "lesson_id": null,
  "title": "Acids lesson",
  "style": "simple",
  "created_at": "2026-06-05T00:00:00Z",
  "updated_at": "2026-06-05T00:00:00Z",
  "messages": []
}
```

Error responses:
- `401`, `422`.

Service function called:
- `create_session`

Status:
- Existing.

Files:
- Existing: `backend/app/api/chat/routes.py`, `backend/app/schemas/chat.py`, `backend/app/services/chat_service.py`, `backend/app/models/chat.py`.

### API Order 14 - Chat Ask

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/chat/ask`

Purpose:
- Return a RAG-grounded Arabic tutor answer with page sources and confidence.

Called by:
- Mobile app main chat screen.

Calls:
- `chat_service.ask_question`
- `retrieve_context`
- `ai_service.get_ai_response` when Gemini is available and route requires generated answer.

Database tables:
- Reads `rag_chunks`, `content_sources`.
- May write `chat_sessions`, `chat_messages` depending service path.

Request:

```json
{
  "question": "اشرح لي ما هي الحموض من الكتاب؟",
  "lesson_id": null,
  "topic_id": null,
  "source_types": ["textbook"],
  "preferred_answer_type": "auto",
  "answer_scope": "book_only"
}
```

Response:

```json
{
  "answer": "الحموض هي مواد...",
  "answer_type": "text",
  "route": "textbook_rag",
  "grounding": "book",
  "answer_scope": "book_only",
  "blocks": [],
  "sources": [
    {
      "chunk_id": 13,
      "source_id": 1,
      "source": "Grade 9 Chemistry",
      "page_number": 11,
      "content_type": "text",
      "similarity_score": 0.82
    }
  ],
  "source_blocks": [
    {
      "book_id": "grade_9_chemistry",
      "page": 11,
      "chunk_id": 13,
      "chunk_type": "text",
      "score": 0.82
    }
  ],
  "page_numbers": [11, 13],
  "confidence": 0.82,
  "diagnostics": {},
  "suggested_next_action": "اسأل عن مثال أو حل تمرين."
}
```

Error responses:
- `401`, `422`.
- `503` AI unavailable if no local fallback is allowed.
- Gemini `429` quota should return graceful local RAG answer if possible.

Service function called:
- `ask_question`

Status:
- Existing, with known quality dependency on complete ingestion and real embeddings.

Files:
- Existing: `backend/app/api/chat/routes.py`, `backend/app/schemas/chat.py`, `backend/app/services/chat_service.py`, `backend/app/services/ai_service.py`.

### API Order 15 - Gemini AI Tutor Generation

Type:
- External Provider API

Purpose:
- Generate the final Arabic explanation after retrieval and routing.

Called by:
- `chat_service.ask_question`
- `homework_service.solve_text`
- AI quiz/flashcard generators.

Calls:
- `client.models.generate_content(...)`

Database tables:
- None directly.
- Chat/homework services persist generated outputs.

Request:

```json
{
  "model": "gemini-3.5-flash",
  "system_prompt": "You are EduMind...",
  "messages": [
    {"role": "user", "content": "ما هي الحموض؟"}
  ]
}
```

Response:

```json
{
  "text": "الحموض هي..."
}
```

Error responses:
- Missing Gemini key.
- Quota/rate limit.
- Timeout.
- Empty response.

Service function called:
- `ai_service.get_ai_response`

Status:
- Existing. It returns local/test text when Gemini is missing and handles quota errors.

Files:
- Existing: `backend/app/services/ai_service.py`, `backend/app/services/gemini_client.py`.

### API Order 16 - Chat Feedback

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/chat/messages/{message_id}/feedback`

Purpose:
- Store user feedback for a chat message.

Called by:
- Mobile app after an answer.

Calls:
- `chat_service.update_message_feedback`

Database tables:
- `chat_messages`

Request:

```json
{
  "feedback": "helpful"
}
```

Response:

```json
{
  "id": 10,
  "session_id": 1,
  "role": "assistant",
  "content": "الحموض هي...",
  "format": "text",
  "feedback": "helpful",
  "media_url": null,
  "latency_ms": 900,
  "created_at": "2026-06-05T00:00:00Z"
}
```

Error responses:
- `401`, `404`, `422`.

Service function called:
- `update_message_feedback`

Status:
- Existing.

Files:
- Existing: `backend/app/api/chat/routes.py`, `backend/app/schemas/chat.py`, `backend/app/services/chat_service.py`.

### API Order 17 - Quiz Generation

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/quizzes/generate`

Purpose:
- Return quiz questions from reviewed/extracted question bank.

Called by:
- Mobile quiz/exam trainer.

Calls:
- `quiz_service.generate_quiz`

Database tables:
- `extracted_questions`

Request:

```json
{
  "topic_id": 1,
  "source_type": "textbook",
  "difficulty": 2,
  "limit": 5
}
```

Response:

```json
{
  "questions": [
    {
      "id": 1,
      "question_text": "ما تعريف الحمض؟",
      "question_type": "short_answer",
      "options": null,
      "page_number": 11,
      "source_id": 1,
      "difficulty": 2
    }
  ]
}
```

Error responses:
- `422`.
- `404` no reviewed questions if strict mode is added.

Service function called:
- `generate_quiz`

Status:
- Partial. Existing route reads extracted questions. AI generation helper exists but is not wired into this endpoint.

Files:
- Existing: `backend/app/api/quizzes.py`, `backend/app/schemas/quiz.py`, `backend/app/services/quiz_service.py`, `backend/app/services/ai_quiz_generator.py`.

### API Order 18 - Gemini Quiz/Question Generation

Type:
- External Provider API

Purpose:
- Generate new questions from RAG context when the extracted/reviewed bank is insufficient.

Called by:
- Target quiz generation workflow.
- Current helper `generate_questions_for_topic`, but not current route.

Calls:
- `ai_service.get_ai_response`

Database tables:
- `extracted_questions`

Request:

```json
{
  "topic_id": 1,
  "num_questions": 5,
  "context": "retrieved textbook context..."
}
```

Response:

```json
{
  "questions": [
    {
      "question_text": "ما تعريف الحمض؟",
      "options": ["..."],
      "correct_answer": "...",
      "explanation": "...",
      "difficulty": 1,
      "page_number": 11,
      "needs_review": true
    }
  ]
}
```

Error responses:
- Gemini unavailable/quota.
- Invalid JSON.
- Empty generated list.

Service function called:
- `ai_quiz_generator.generate_questions_for_topic`

Status:
- Partial. The helper manually parses JSON text and is not exposed as a clear Swagger API.

Files:
- Existing: `backend/app/services/ai_quiz_generator.py`.
- Modify later: `backend/app/api/quizzes.py`, `backend/app/schemas/quiz.py`.

### API Order 19 - Quiz Submission

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/quizzes/submit`

Purpose:
- Grade answers and record weak topics.

Called by:
- Mobile quiz UI.

Calls:
- `quiz_service.submit_quiz`

Database tables:
- `extracted_questions`, `quiz_attempts`

Request:

```json
{
  "topic_id": 1,
  "answers": {
    "1": "الحموض مواد تعطي H+"
  }
}
```

Response:

```json
{
  "attempt_id": 1,
  "score": 1,
  "total": 1,
  "weak_topics": {}
}
```

Error responses:
- `401`, `422`.

Service function called:
- `submit_quiz`

Status:
- Existing, but grading is exact-match MVP.

Files:
- Existing: `backend/app/api/quizzes.py`, `backend/app/schemas/quiz.py`, `backend/app/services/quiz_service.py`.

### API Order 20 - Exam Practice

Type:
- Internal FastAPI Swagger API

Endpoint:
- `GET /api/v1/exams/practice`

Purpose:
- Return exam-style practice questions.

Called by:
- Mobile exam trainer.

Calls:
- `quiz_service.generate_quiz(topic_id=None, source_type="exam", limit=10)`

Database tables:
- `extracted_questions`

Request:

```json
{}
```

Response:

```json
{
  "questions": []
}
```

Error responses:
- `422`, `404` if strict no-questions behavior is added.

Service function called:
- `generate_quiz`

Status:
- Partial. `source_type="exam"` is currently not fully filtered through `ContentSource`.

Files:
- Existing: `backend/app/api/exams.py`, `backend/app/services/quiz_service.py`.

### API Order 21 - Homework Solve Text

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/homework/solve-text`

Purpose:
- Solve a typed chemistry homework problem using RAG context and Gemini tutor generation.

Called by:
- Mobile homework text UI.

Calls:
- `homework_service.solve_text`
- `retrieve_context`
- `ai_service.get_ai_response`

Database tables:
- `homework`, reads `rag_chunks`

Request:

```json
{
  "problem_text": "احسب عدد مولات ...",
  "topic_id": null
}
```

Response:

```json
{
  "id": 1,
  "user_id": 1,
  "topic_id": null,
  "image_url": null,
  "problem_text": "احسب عدد مولات ...",
  "extracted_text": null,
  "solution": "خطوات الحل...",
  "source_chunks": null,
  "confidence_score": 0.8,
  "created_at": "2026-06-05T00:00:00Z",
  "updated_at": "2026-06-05T00:00:00Z"
}
```

Error responses:
- `401`, `422`.
- `503` Gemini unavailable if no local fallback is allowed.

Service function called:
- `solve_text`

Status:
- Existing, but `source_chunks` is not filled.

Files:
- Existing: `backend/app/api/homework.py`, `backend/app/schemas/homework.py`, `backend/app/services/homework_service.py`.

### API Order 22 - Homework Solve Image

Type:
- Internal FastAPI Swagger API

Endpoint:
- `POST /api/v1/homework/solve-image`

Purpose:
- Extract text from a homework photo/image, then solve it with the text homework solver.

Called by:
- Mobile homework photo UI.

Calls:
- `homework_service.solve_image`
- `GeminiVisionProvider.extract_page`
- `homework_service.solve_text`

Database tables:
- `homework`, reads `rag_chunks`

Request:

```json
{
  "image_path": "/absolute/or/server/path/homework.png",
  "topic_id": null
}
```

Response:

```json
{
  "id": 1,
  "user_id": 1,
  "topic_id": null,
  "image_url": "/absolute/or/server/path/homework.png",
  "problem_text": "extracted problem text",
  "extracted_text": "extracted problem text",
  "solution": "خطوات الحل...",
  "source_chunks": null,
  "confidence_score": 0.8,
  "created_at": "2026-06-05T00:00:00Z",
  "updated_at": "2026-06-05T00:00:00Z"
}
```

Error responses:
- `401`, `404` image not found, `422`, `503` Gemini not configured.

Service function called:
- `solve_image`

Status:
- Partial. Current route is server-path based, not mobile upload-ready.

Files:
- Existing: `backend/app/api/homework.py`, `backend/app/schemas/homework.py`, `backend/app/services/homework_service.py`.
- Modify later: add upload handling or asset API.

### API Order 23 - Gemini Homework Image Understanding

Type:
- External Provider API

Purpose:
- Understand a homework/problem image and produce structured extracted text.

Called by:
- `homework_service.solve_image`.

Calls:
- `GeminiVisionProvider.extract_page`.

Database tables:
- None directly. Result is written to `homework.extracted_text`.

Request:

```json
{
  "image_path": "homework.png",
  "page_number": 1,
  "source_type": "homework"
}
```

Response:

```json
{
  "page_number": 1,
  "sections": [
    {
      "heading": null,
      "content": "extracted problem",
      "content_type": "exercise"
    }
  ],
  "warnings": []
}
```

Error responses:
- Missing Gemini key.
- Image not found.
- Invalid/empty extraction.
- Quota/rate limit.

Service function called:
- `GeminiVisionProvider.extract_page`

Status:
- Existing as provider call, partial as mobile product flow.

Files:
- Existing: `backend/app/services/homework_service.py`, `backend/app/services/ocr/gemini_provider.py`.

### API Order 24 - Flashcard Generation

Type:
- Internal FastAPI Swagger API

Endpoint:
- Existing manual creation: `POST /api/v1/flashcards`
- Proposed AI generation: `POST /api/v1/flashcards/generate`

Purpose:
- Generate study flashcards from textbook context.

Called by:
- Mobile revision UI.
- Admin/teacher review tools.

Calls:
- Existing route calls `flashcard_service.create_flashcard`.
- Proposed route should call `ai_flashcard_generator.generate_flashcards_for_topic`.

Database tables:
- `flashcards`, `flashcard_progress`, reads `rag_chunks`

Request:

```json
{
  "topic_id": 1,
  "limit": 5,
  "source_types": ["textbook"]
}
```

Response:

```json
{
  "flashcards": [
    {
      "id": 1,
      "topic_id": 1,
      "front_ar": "ما تعريف الحمض؟",
      "back_ar": "الحموض مواد تعطي H+...",
      "created_by": "ai"
    }
  ],
  "needs_review": true
}
```

Error responses:
- `401`, `403` for admin-only generation if protected.
- `422`.
- `503` Gemini unavailable.

Service function called:
- Existing: `flashcard_service.create_flashcard`
- Proposed: `flashcard_service.generate_ai_flashcards`

Status:
- Partial. Manual flashcard route exists. AI generator service exists but is not exposed in Swagger.

Files:
- Existing: `backend/app/api/flashcards.py`, `backend/app/schemas/flashcards.py`, `backend/app/services/flashcard_service.py`, `backend/app/services/ai_flashcard_generator.py`.
- Modify later: add generation schemas and route.

### API Order 25 - Admin Question Review

Type:
- Internal FastAPI Swagger API

Endpoints:
- `GET /api/v1/admin/ingestion/questions/unreviewed`
- `POST /api/v1/admin/ingestion/questions/{question_id}/review`

Purpose:
- Review and approve extracted or AI-generated questions before they are trusted.

Called by:
- Admin review dashboard and Swagger.

Calls:
- Direct DB query/update.

Database tables:
- `extracted_questions`

Request:

```json
{
  "question_text": "ما تعريف الحمض؟",
  "question_type": "short_answer",
  "options": null,
  "correct_answer": "الحموض مواد تعطي H+ عند انحلالها في الماء.",
  "explanation": "من تعريف الحموض في الكتاب.",
  "answer_source": "manual",
  "difficulty": 1,
  "needs_review": false
}
```

Response:

```json
{
  "id": 1,
  "source_id": 1,
  "chapter_id": null,
  "lesson_id": null,
  "topic_id": null,
  "page_number": 11,
  "question_text": "ما تعريف الحمض؟",
  "question_type": "short_answer",
  "options": null,
  "correct_answer": "الحموض مواد تعطي H+ عند انحلالها في الماء.",
  "explanation": "من تعريف الحموض في الكتاب.",
  "answer_source": "manual",
  "difficulty": 1,
  "needs_review": false,
  "metadata_json": {}
}
```

Error responses:
- `401`, `403`, `404`, `422`.

Service function called:
- Missing dedicated service.

Status:
- Partial. Endpoints exist but route contains business logic and sync DB.

Files:
- Existing: `backend/app/api/ingestion/routes.py`, `backend/app/schemas/ingestion.py`, `backend/app/models/textbook.py`.

### API Order 26 - AI Health / Config Check

Type:
- Internal FastAPI Swagger API

Endpoint:
- Proposed: `GET /api/v1/health/ai-config`

Purpose:
- Show whether required AI services are configured and whether the current config can run production ingestion.

Called by:
- Swagger before ingestion.
- Admin dashboard.
- Mobile debug screen if needed.

Calls:
- Settings inspection.
- Optional DB/Redis/Celery checks.

Database tables:
- Optional none.

Request:

```json
{}
```

Response:

```json
{
  "gemini_configured": true,
  "document_model": "gemini-3.5-flash",
  "document_fallback_model": "gemini-2.5-pro",
  "embedding_model": "text-embedding-004",
  "embedding_dim": 768,
  "pdf_direct_extraction_enabled": true,
  "pdf_image_fallback_enabled": true,
  "ingestion_mode": "production",
  "vector_store": "postgres_pgvector",
  "redis_configured": true,
  "celery_configured": true,
  "production_ready": true,
  "warnings": []
}
```

Error responses:
- `503` if required dependencies are down and strict readiness is requested.

Service function called:
- Missing: `ai_health_service.get_ai_config_status`.

Status:
- Missing.

Files:
- Create/modify: `backend/app/schemas/common.py` or `backend/app/schemas/ai_health.py`, `backend/app/services/ai_health_service.py`, `backend/app/api/health.py`.

## Minimum Mobile RAG Route Order

For a mobile app that only needs RAG chat first, use this order:

1. `POST /api/v1/auth/register` or `POST /api/v1/auth/login` to get a bearer token.
2. `GET /api/v1/health` to verify the backend is reachable.
3. `GET /api/v1/health/ai-config` once implemented, to verify RAG/AI readiness.
4. `POST /api/v1/rag/retrieve` to test whether the book returns relevant source chunks.
5. `POST /api/v1/chat/sessions` to create a conversation.
6. `POST /api/v1/chat/ask` to ask the textbook-grounded question.
7. `POST /api/v1/chat/messages/{message_id}/feedback` if the mobile app stores answer quality.

The mobile app should not call Gemini directly. It should call the backend only. The backend owns provider keys, RAG retrieval, citations, safety checks, and fallback behavior.

## Most Important Current Gaps

1. The book is not fully production-ingested: 56 cached pages are failed/empty.
2. `POST /admin/ingestion/start` must use Celery instead of FastAPI in-memory background state.
3. Current model defaults do not match the target config:
   - Target `GEMINI_DOCUMENT_MODEL`: `gemini-3.5-flash`
   - Target `GEMINI_DOCUMENT_FALLBACK_MODEL`: `gemini-2.5-pro`
   - Target `GEMINI_EMBEDDING_MODEL`: `text-embedding-004`
4. There is no AI config/readiness endpoint in Swagger.
5. There is no single-page extraction smoke test endpoint in Swagger.
6. Homework image solving is not mobile-upload-ready.
7. AI flashcard generation is not exposed as a Swagger API.
8. Admin ingestion/review routes should use async DB and stricter admin protection.
9. Redis exists but is not yet used for RAG cache or durable job progress.
10. Chat citations/diagnostics are returned but not clearly persisted with assistant messages.
