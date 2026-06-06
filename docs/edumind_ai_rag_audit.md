# EduMind AI/RAG Codebase Audit

**Date:** 2026-06-03
**Auditor:** Senior Backend Architect & AI/RAG Code Auditor
**Scope:** All AI APIs, RAG APIs, ingestion APIs, database models, service layers, and external Gemini calls

---

## 1. Executive Summary

The EduMind backend has a **mature and well-implemented** AI/RAG system for a chemistry tutor MVP. The core pipeline — PDF ingestion → OCR/Gemini extraction → chunking → embedding → pgvector storage → hybrid retrieval → Gemini generation with fallback — is **fully implemented end-to-end**.

### What Is Implemented ✅
- **7 external Gemini API integrations** (chat generation, embeddings, OCR/PDF extraction, structured JSON mode, file upload, fallback model routing)
- **8 AI/Chat/Homework endpoints** with RAG context injection
- **17 admin ingestion endpoints** covering full PDF lifecycle
- **2 direct RAG retrieval endpoints** (search + retrieve)
- **Sophisticated hybrid scoring** with Arabic normalization, term expansion, intent-based boosting, and chemistry-specific re-ranking
- **Redis caching** for RAG results with versioned keys
- **Dual-path architecture**: pgvector on PostgreSQL, Python cosine fallback on SQLite
- **Complete OCR pipeline** with Gemini Files API → PDF extraction → 300 DPI image fallback → model fallback chain
- **Deterministic routing** for chemistry formulas, reactions, and definitions before RAG
- **Chemistry dictionary** with approved entities and book validation
- **Structured diagnostics logging** for every retrieval request

### What Is Partial ⚠️
- **retry-page** endpoint marks pages for retry but does NOT re-run extraction (line 364: `"Full per-page retry worker is not implemented yet."`)
- **Quiz generation** endpoint serves pre-extracted questions only — the AI quiz generator service exists but is NOT wired to the route
- **Study plan creation** endpoint is CRUD-only — the AI study plan generator exists but is NOT wired to the route
- **Flashcard creation** is admin-manual only — the AI flashcard generator exists but is NOT wired to the route
- **Celery worker** is configured but ingestion routes use `BackgroundTasks` (FastAPI) instead

### What Is Missing ❌
- No multipart PDF upload endpoint (path-based only)
- No dedicated RAG debug API (diagnostics exist in logs only)
- No RAG evaluation/golden-set endpoint
- No RAG feedback collection endpoint
- No chunk inspect/edit/approve/reject endpoints
- No cache invalidation endpoint
- No reindex endpoint
- No streaming chat endpoint
- No AI usage/cost monitoring endpoint

---

## 2. External AI API Call Map

| # | Service | File | Function/Class | Model | API Method | Input | Output | Sync/Async | Validation | Fallback | Retry | Risk |
|---|---------|------|----------------|-------|------------|-------|--------|------------|------------|----------|-------|------|
| 1 | **Tutor chat** | [ai_service.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_service.py#L59-L94) | `get_ai_response()` | `settings.model_name` (`gemini-3.5-flash`) | `client.models.generate_content()` | Conversation messages list | Plain text string | `asyncio.to_thread` ✅ | Response `.text` only — no JSON validation | Quota → Arabic error message; Error → Arabic error message; No key → local test stub | 5 HTTP retries via `HttpRetryOptions` | **Medium** — no structured output; Gemini can hallucinate freely |
| 2 | **Document embedding** | [embeddings.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L37-L58) | `embed_text()` | `settings.gemini_embedding_model` (`gemini-embedding-001`) | `client.models.embed_content()` | Single text string | 768-dim float vector | `asyncio.to_thread` ✅ | Checks `len(embeddings) > 0` | Hash-based fallback embedding | No explicit retry | **Low** |
| 3 | **Query embedding** | [embeddings.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L61-L82) | `embed_query()` | `gemini-embedding-001` | `client.models.embed_content()` | Query string | 768-dim float vector | `asyncio.to_thread` ✅ | Checks `len(embeddings) > 0` | Hash-based fallback embedding | No explicit retry | **Low** |
| 4 | **Batch embedding** | [embeddings.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L85-L114) | `embed_batch()` | `gemini-embedding-001` | `client.models.embed_content()` | List of texts (batch_size=100) | List of 768-dim vectors | `asyncio.to_thread` ✅ | Checks `len(embeddings) == len(batch)` | Per-batch hash fallback | No explicit retry | **Low** |
| 5 | **OCR/PDF extraction (primary)** | [gemini_provider.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L133-L157) | `GeminiVisionProvider._generate_result()` | `settings.gemini_document_model` (`gemini-3-flash-preview`) | `client.models.generate_content()` | PDF Part + prompt | `PageExtractionResult` (structured JSON) | `asyncio.to_thread` ✅ | `response_schema=PageExtractionResult`, `response_mime_type="application/json"`, Pydantic validation, quality gate | Falls back to next model in chain | 5 HTTP retries | **Medium** — quality gate can reject good extractions |
| 6 | **OCR/PDF extraction (fallback model)** | [gemini_provider.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L193-L246) | `_extract_with_model_routing()` | `settings.gemini_document_fallback_model` (`gemini-3.1-flash-lite`) | `client.models.generate_content()` | Same as primary | Same structured JSON | `asyncio.to_thread` ✅ | Same quality gate | Raises `GeminiExtractionQualityError` if both fail | 5 HTTP retries | **Medium** |
| 7 | **Gemini Files API upload** | [gemini_provider.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L248-L294) | `GeminiVisionProvider.upload_pdf()` | N/A | `client.files.upload()` | PDF file path | `UploadedDocument` (name, URI, mime) | `asyncio.to_thread` ✅ | Polls file state for ACTIVE (30 iterations × 2s), checks for FAILED | Returns `None` → image fallback | No explicit retry | **Medium** — 60s polling timeout |
| 8 | **OCR/image fallback (300 DPI)** | [gemini_provider.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L337-L370) | `GeminiVisionProvider.extract_page()` | Same model routing chain | `client.models.generate_content()` | PNG image bytes + prompt | `PageExtractionResult` | `asyncio.to_thread` ✅ | Same quality gate | None — last resort | 5 HTTP retries | **Low** |
| 9 | **Deterministic fallback embedding** | [embeddings.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L19-L28) | `_fallback_embedding()` | N/A (local) | SHA-256 hash | Text string | 768-dim normalized vector | Synchronous | N/A | N/A | N/A | **Low** — dev only |
| 10 | **Local RAG fallback** | [chat_service.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chat_service.py#L1033-L1078) | `_local_rag_answer()` | N/A (local) | Lexical extraction | Question + chunks | Formatted Arabic text | Synchronous | N/A | N/A | N/A | **Low** |

### Key observations on task types
- **Document embeddings** use `RETRIEVAL_DOCUMENT` task type ([embeddings.py:47](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L47))
- **Query embeddings** use `RETRIEVAL_QUERY` task type ([embeddings.py:71](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L71))
- This is **correct** per Gemini embedding best practices ✅

### Model names in config ([config.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/core/config.py#L21-L25))
| Setting | Default Value | Purpose |
|---------|---------------|---------|
| `model_name` | `gemini-3.5-flash` | Tutor chat generation |
| `gemini_document_model` | `gemini-3-flash-preview` | Primary OCR/document extraction |
| `gemini_document_fallback_model` | `gemini-3.1-flash-lite` | OCR fallback when primary fails quality |
| `gemini_embedding_model` | `gemini-embedding-001` | RAG embeddings |

---

## 3. Implemented AI/RAG Backend APIs

### A. Implemented AI APIs

| Method | Path | Purpose | Auth | Request Schema | Response Schema | File | Status |
|--------|------|---------|------|----------------|-----------------|------|--------|
| POST | `/api/v1/chat/sessions/{session_id}/messages` | Multi-turn AI chat | Bearer | `SendMessageRequest` | `MessageResponse` | [chat/routes.py:57](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L57) | ✅ Implemented |
| POST | `/api/v1/chat/ask` | Stateless RAG answer | Bearer | `ChatAskRequest` | `ChatAnswerResponse` | [chat/routes.py:73](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L73) | ✅ Implemented |
| POST | `/api/v1/homework/solve-text` | Solve typed homework | Bearer | `HomeworkSolveTextRequest` | `HomeworkResponse` | [homework.py:14](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/homework.py#L14) | ✅ Implemented |
| POST | `/api/v1/homework/solve-image` | OCR image → solve | Bearer | `HomeworkSolveImageRequest` | `HomeworkResponse` | [homework.py:23](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/homework.py#L23) | ✅ Implemented |
| POST | `/api/v1/quizzes/generate` | Generate quiz | Public | `QuizGenerateRequest` | `QuizGenerateResponse` | [quizzes.py:22](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/quizzes.py#L22) | ⚠️ Partial — uses pre-extracted questions only, NOT the AI generator |
| GET | `/api/v1/quizzes/recommendations` | AI-recommended quizzes | Public | N/A | `list[QuizRecommendationResponse]` | [quizzes.py:61](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/quizzes.py#L61) | ⚠️ Partial — deterministic topic ordering, no AI |
| POST | `/api/v1/study-plans` | Create study plan | Bearer | `StudyPlanCreate` | `StudyPlanResponse` | [study_plans.py:25](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/study_plans.py#L25) | ⚠️ Partial — CRUD only, AI generator NOT wired |
| POST | `/api/v1/flashcards` | Create flashcard | Admin | `FlashcardCreateRequest` | `FlashcardResponse` | [flashcards.py:24](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/flashcards.py#L24) | ⚠️ Partial — manual admin creation only, AI generator NOT wired |
| POST | `/api/v1/chat/messages/{message_id}/feedback` | Message feedback | Bearer | `MessageFeedbackRequest` | `MessageResponse` | [chat/routes.py:115](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L115) | ✅ Implemented |

### B. Implemented RAG APIs

| Method | Path | Purpose | Auth | File | Status |
|--------|------|---------|------|------|--------|
| GET | `/api/v1/rag/search` | Vector/hybrid search | Bearer | [rag/routes.py:31](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/rag/routes.py#L31) | ✅ Implemented |
| POST | `/api/v1/rag/retrieve` | JSON body retrieval | Bearer | [rag/routes.py:59](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/rag/routes.py#L59) | ✅ Implemented |

### C. Implemented Ingestion/Admin APIs

| Method | Path | Purpose | Auth | File | Status |
|--------|------|---------|------|------|--------|
| POST | `/api/v1/admin/ingestion/start` | Start PDF ingestion | Admin | [ingestion/routes.py:169](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L169) | ✅ Implemented |
| GET | `/api/v1/admin/ingestion/status/{task_id}` | Poll progress | Admin | [ingestion/routes.py:245](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L245) | ✅ Implemented |
| GET | `/api/v1/admin/ingestion/sources` | List sources | Admin | [ingestion/routes.py:202](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L202) | ✅ Implemented |
| POST | `/api/v1/admin/ingestion/sources` | Register source | Admin | [ingestion/routes.py:210](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L210) | ✅ Implemented |
| GET | `/api/v1/admin/ingestion/sources/{source_id}` | Source details | Admin | [ingestion/routes.py:233](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L233) | ✅ Implemented |
| DELETE | `/api/v1/admin/ingestion/source/{source_id}` | Delete source + chunks | Admin | [ingestion/routes.py:307](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L307) | ✅ Implemented |
| DELETE | `/api/v1/admin/ingestion/sources/{source_id}` | Delete (alternate path) | Admin | [ingestion/routes.py:327](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L327) | ✅ Implemented |
| GET | `/api/v1/admin/ingestion/stats` | Global statistics | Admin | [ingestion/routes.py:253](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L253) | ✅ Implemented |
| DELETE | `/api/v1/admin/ingestion/clear` | Clear all chunks | Admin | [ingestion/routes.py:297](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L297) | ✅ Implemented |
| GET | `/api/v1/admin/ingestion/pages/{source_id}` | Per-page status | Admin | [ingestion/routes.py:336](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L336) | ✅ Implemented |
| POST | `/api/v1/admin/ingestion/retry-page/{page_id}` | Retry failed page | Admin | [ingestion/routes.py:350](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L350) | ⚠️ Partial — marks status only, does NOT re-run extraction |
| POST | `/api/v1/admin/ingestion/test-query` | Test RAG retrieval | Admin | [ingestion/routes.py:368](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L368) | ✅ Implemented |
| POST | `/api/v1/admin/ingestion/test-chunk/{chunk_id}` | Find similar chunks | Admin | [ingestion/routes.py:392](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L392) | ✅ Implemented |
| GET | `/api/v1/admin/ingestion/questions/unreviewed` | Unreviewed questions | Admin | [ingestion/routes.py:429](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L429) | ✅ Implemented |
| POST | `/api/v1/admin/ingestion/questions/{question_id}/review` | Review question | Admin | [ingestion/routes.py:444](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L444) | ✅ Implemented |

---

## 4. RAG Retrieval Implementation

### Retrieval Flow (as found in code)

```
User query
  ↓
clean_query()          — strip instruction noise phrases (rag.py:182)
  ↓
rewrite_query()        — expand with Arabic synonyms/chemical terms (rag.py:190)
  ↓
_query_terms()         — tokenize, remove stopwords, strip ال/ات/يه suffixes,
                         expand via _TERM_EXPANSIONS dictionary (rag.py:275)
  ↓
embed_query()          — Gemini text-embedding-001 with RETRIEVAL_QUERY task type
                         OR hash fallback (embeddings.py:61)
  ↓
Redis cache check      — key: "rag_cache:v6:<md5>" TTL=3600s (rag.py:450-465)
  ↓
PostgreSQL pgvector    — cosine_distance() ordering, fetch top_k*12 candidates (rag.py:502)
  OR SQLite fallback   — load all chunks, compute cosine in Python (rag.py:506-508)
  ↓
For each candidate:
  vector_score         — cosine similarity (Python, rag.py:252-261)
  lexical_score        — Arabic-normalized token + substring matching (rag.py:298-335)
  hybrid_score         — 0.35*vector + 0.65*lexical, then max(blended, lexical, vector),
                         plus intent-based boosting and chemical entity bonuses (rag.py:338-393)
  ↓
Filter by min_similarity, sort desc, take top_k
  ↓
Log diagnostics via RetrievalDiagnostics (rag_diagnostics.py)
  ↓
Cache results to Redis (rag.py:561-571)
```

### Exact Scoring Formula ([rag.py:338-393](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py#L338-L393))

```
lexical_score = min(0.72, exact_hits*0.12 + substring_hits*0.06)
              + min(0.2, original_ratio*0.2)
              + chemistry-specific bonuses (acid/base ion matching: +0.16/+0.22)

blended = 0.35 * max(vector_score, 0) + 0.65 * lexical_score
score   = max(blended, lexical_score, vector_score)

Intent boosting:
  definition_lookup → +0.18 for definition content types, -0.32 for objectives
  equation_lookup   → +0.18 for equation content types, -0.10 for definitions
  reaction_query    → copper+sulfuric acid bonuses up to +0.70

Chemical formula match → +0.10

Final: clamp to [0.0, 1.0]
```

### Arabic Normalization ([rag.py:35-48](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py#L35-L48))
- ✅ Diacritics removal (Unicode range \u0610-\u06ED)
- ✅ Alef normalization (أ/إ/آ/ٱ → ا)
- ✅ Yaa normalization (ئ → ي, ى → ي)
- ✅ Taa marbuta normalization (ة → ه)
- ✅ Waw normalization (ؤ → و)
- ✅ Stopword removal (40+ Arabic stopwords at rag.py:53-66)
- ⚠️ **No stemming** — uses suffix stripping only (ال prefix, ات/يه suffixes)
- ✅ Term expansion dictionary with 14 chemical concept groups (rag.py:71-150)

### Redis Cache ([rag.py:444-465](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py#L444-L465))
- **Key format:** `rag_cache:v6:<md5(query|user_id|chapter_id|lesson_id|topic_id|source_types|content_types|top_k|min_similarity|intent)>`
- **TTL:** 3600 seconds (1 hour)
- **What is cached:** Serialized list of `RetrievedChunk` dicts
- **Connection pool:** 10 max connections ([redis.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/core/redis.py))

### pgvector Configuration
- **Vector dimension:** 768 ([textbook.py:18](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L18), [embeddings.py:15](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L15))
- **Similarity method:** Cosine distance (`cosine_distance()` at [rag.py:502](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py#L502))
- **Index type:** IVFFlat with `vector_cosine_ops`, 100 lists ([textbook.py:75-81](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L75-L81))
- **SQLite fallback:** JSON column with Python cosine similarity ([textbook.py:16-19](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L16-L19))

### Confidence Threshold
- `_MIN_BOOK_GROUNDED_CONFIDENCE = 0.25` ([chat_service.py:39](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chat_service.py#L39))
- When below threshold → returns "not_found" response with suggestion to rephrase
- ⚠️ Comment in code says to raise to 0.45–0.55 once real Gemini embeddings are active

### Source Traceability
- ✅ Each `RetrievedChunk` carries `source_id`, `page_number`, `chapter_id`, `lesson_id`, `topic_id`
- ✅ Source page images are served via `_page_image_url()` for frontend display
- ✅ `source_blocks` in chat responses include `book_id`, `page`, `chunk_id`, `chunk_type`, `score`

---

## 5. OCR / Document Ingestion Implementation

### Full Ingestion Flow ([ingestion_pipeline.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ingestion_pipeline.py))

```
POST /admin/ingestion/start
  ↓
_get_or_create_source()      — find or create ContentSource row (line 463)
  ↓
get_vision_provider()        — always GeminiDocumentProvider (ocr/__init__.py:8)
  ↓
classify_pages()             — PyMuPDF per-page text detection → SELECTABLE_TEXT / NEEDS_VISION / MIXED_VISION
  ↓
upload_pdf()                 — Gemini Files API upload, polls ACTIVE state (gemini_provider.py:248)
  ↓
For each page 1..N:
  _extract_page()
    ├─ SELECTABLE_TEXT → PyMuPDF text extraction only
    ├─ NEEDS_VISION/MIXED_VISION:
    │   ├─ Try: extract_page_from_pdf() via uploaded PDF reference
    │   │   ├─ Primary model (gemini-3-flash-preview)
    │   │   └─ Quality gate → fallback model (gemini-3.1-flash-lite)
    │   ├─ Quality gate fail → render_page_to_image(300 DPI)
    │   └─ extract_page() via rendered image
    └─ Merge text + vision sections via deduplicate_sections()
  ↓
_write_page_cache()          — JSON file per page
  ↓
_store_page_chunks()         — build_page_chunk_records() → embed_batch() → RagChunk INSERT
  ↓
_store_questions()           — ExtractedQuestion INSERT with needs_review flag
  ↓
Source status → completed / completed_with_warnings / failed / dry_run_incomplete
```

### Quality Gate ([ocr/quality.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/quality.py) + [ingestion_pipeline.py:189-206](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ingestion_pipeline.py#L189-L206))
- Checks: schema validity, non-empty sections, structured content presence
- `gemini_min_page_chars = 40` (too few chars → quality failure)
- `gemini_min_completeness_score = 0.5` (below → quality failure)
- Quality issues trigger model fallback chain

---

## 6. Database Model Verification

| Model | Table | Key Columns | Relationships | Indexes | Issues |
|-------|-------|-------------|---------------|---------|--------|
| **ContentSource** | `content_sources` | id, source_type, title, grade, subject, year, file_path, original_filename, status, metadata_json | →RagChunk, →ExtractedQuestion (cascade delete) | source_type, year, status, id | ✅ None |
| **RagChunk** | `rag_chunks` | id, source_id, chapter_id, lesson_id, topic_id, page_number, chunk_index, content, normalized_content, content_type, source_type, extraction_method, language, embedding(768), metadata_json | →ContentSource, →Chapter, →Lesson, →Topic | source_id, chapter_id, lesson_id, topic_id, page_number, content_type, source_type, **embedding (IVFFlat cosine)** | ✅ Comprehensive indexes |
| **ExtractedQuestion** | `extracted_questions` | id, source_id, chapter_id, lesson_id, topic_id, page_number, question_text, question_type, options, correct_answer, explanation, answer_source, difficulty, needs_review, metadata_json | →ContentSource, →Chapter, →Lesson, →Topic | source_id, chapter_id, topic_id, needs_review | ✅ None |
| **TextbookChunk** | `textbook_chunks` | id, chapter_id, page_number, content, source, source_type, extraction_method, embedding | →Chapter | chapter_id, page_number | ⚠️ **Legacy table** — kept for compatibility but NOT used by current RAG |
| **IngestionJob** | `ingestion_jobs` | id, job_uid, source_id, status, progress, message, result_json, errors_json | →ContentSource | job_uid (unique), source_id, status | ✅ None |
| **IngestionPage** | `ingestion_pages` | id, source_id, job_id, page_number, page_type, status, extraction_methods, cache_path, char_count, completeness_score, warnings_json, errors_json, content_preview | →ContentSource, →IngestionJob | source_id, page_number, status | ✅ None |
| **ChatSession** | `chat_sessions` | id, user_id, lesson_id, title, style | →User, →ChatMessage (cascade delete) | user_id, lesson_id | ✅ None |
| **ChatMessage** | `chat_messages` | id, session_id, role, content, format, feedback, media_url, latency_ms | →ChatSession | session_id | ✅ None |
| **Homework** | `homework` | id, user_id, topic_id, image_url, problem_text, extracted_text, solution, source_chunks, confidence_score | →User, →Topic | user_id, topic_id | ✅ None |
| **StudyPlan** | `study_plans` | id, user_id, exam_date, plan_json, status | →User | user_id | ⚠️ No index on status |

### Migration Status
- Only **1 migration file** exists: `0001_initial_schema.py`
- ⚠️ No migrations specifically for pgvector extension (`CREATE EXTENSION vector`)
- ⚠️ No migrations for IVFFlat index creation
- The code relies on SQLAlchemy's `create_all()` or manual schema setup

---

## 7. Missing APIs to Implement

| Priority | API Name | Method/Path | Why Needed | Suggested Request | Suggested Response |
|----------|----------|-------------|------------|-------------------|--------------------|
| **P0** | PDF Upload | `POST /api/v1/admin/ingestion/upload` | Current `start` requires server-local `pdf_path`. Fragile for deployment. | `multipart/form-data: file, title, source_type, grade` | `{source_id, file_path, status}` |
| **P0** | RAG Debug | `GET /api/v1/rag/debug?query=...` | Diagnostics exist in logs only; no API to inspect scoring | `query, top_k, intent` | `{normalized_query, expansions, candidates: [{chunk_id, vector_score, lexical_score, hybrid_score, snippet}]}` |
| **P0** | RAG Feedback | `POST /api/v1/rag/feedback` | No way to collect user feedback on RAG answer quality | `{query, answer, rating, expected_answer, source_quality}` | `{feedback_id, status}` |
| **P0** | Cancel Ingestion Job | `POST /api/v1/admin/ingestion/jobs/{task_id}/cancel` | Long-running ingestion cannot be stopped | `{}` | `{task_id, status: "cancelled"}` |
| **P1** | Wire AI Quiz Generator | `POST /api/v1/quizzes/generate-ai` | `ai_quiz_generator.py` exists but is dead code | `{topic_id, num_questions}` | `QuizGenerateResponse` |
| **P1** | Wire AI Study Plan | `POST /api/v1/study-plans/generate` | `ai_study_plan.py` exists but is dead code | `{target_date, topics}` | `StudyPlanResponse` |
| **P1** | Wire AI Flashcard Generator | `POST /api/v1/flashcards/generate` | `ai_flashcard_generator.py` exists but is dead code | `{topic_id, num_flashcards}` | `list[FlashcardResponse]` |
| **P1** | RAG Evaluation | `POST /api/v1/rag/evaluate` | No automated measurement of retrieval quality | `{golden_questions: [{query, expected_chunks, expected_answer}]}` | `{precision, recall, source_hit_rate}` |
| **P1** | Chunk Inspect | `GET /api/v1/admin/rag/chunks/{chunk_id}` | No way to inspect individual chunk with metadata | N/A | `{id, content, normalized_content, embedding_preview, source, page, metadata}` |
| **P1** | Chunk Edit | `PATCH /api/v1/admin/rag/chunks/{chunk_id}` | Bad OCR chunks need correction + re-embedding | `{content, content_type, re_embed: true}` | `{chunk_id, updated, re_embedded}` |
| **P1** | Reindex Source | `POST /api/v1/admin/rag/reindex` | Needed when embedding model or normalization changes | `{source_id, all: false}` | `{chunks_reindexed, time_ms}` |
| **P1** | Cache Clear | `POST /api/v1/admin/rag/cache/clear` | Redis cache can serve stale results after ingestion | `{source_id, pattern, all: false}` | `{keys_cleared}` |
| **P1** | Streaming Chat | `POST /api/v1/chat/ask/stream` | Long Gemini responses freeze the UI | SSE `ChatAskRequest` | SSE text chunks |
| **P2** | AI Usage Stats | `GET /api/v1/admin/ai/usage` | No cost/latency monitoring | N/A | `{total_calls, avg_latency_ms, quota_errors, fallback_rate}` |
| **P2** | AI Capabilities | `GET /api/v1/ai/capabilities` | Frontend cannot adapt to available AI features | N/A | `{models, ocr_available, upload_limits}` |
| **P2** | Prompt Test | `POST /api/v1/admin/prompts/test` | No way to test prompt changes | `{prompt, context, query}` | `{answer, latency_ms}` |

---

## 8. Bugs / Risks / Inconsistencies

| # | Severity | File | Evidence | Recommended Fix |
|---|----------|------|----------|-----------------|
| 1 | **Critical** | [ingestion/routes.py:350-365](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L350-L365) | `retry-page` sets status to `"queued_retry"` but **never re-runs extraction**. Message: `"Full per-page retry worker is not implemented yet."` | Implement actual page re-extraction by calling `_extract_page()` + `_store_page_chunks()` |
| 2 | **Critical** | [ingestion/routes.py:368-389](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L368-L389) | `test-query` endpoint passes a sync `Session` to async `retrieve_context()`. Potential runtime error if dialect check fails. | Change to use `get_async_db` dependency |
| 3 | **Critical** | [ingestion/routes.py:392-426](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L392-L426) | `test-chunk` has same sync `Session` → async `retrieve_context()` mismatch | Same fix as above |
| 4 | **High** | [ai_quiz_generator.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_quiz_generator.py) | AI quiz generator is **dead code** — never called from any route. `quiz_service.generate_quiz()` returns pre-extracted questions only. | Wire `generate_questions_for_topic()` to a new `/quizzes/generate-ai` endpoint |
| 5 | **High** | [ai_flashcard_generator.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_flashcard_generator.py) | AI flashcard generator is **dead code** — never called from any route. | Wire to `/flashcards/generate` endpoint |
| 6 | **High** | [ai_study_plan.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_study_plan.py) | AI study plan generator is **dead code** — never called from any route. `study_plan_service.create_study_plan()` is CRUD only. | Wire to `/study-plans/generate` endpoint |
| 7 | **High** | [ai_quiz_generator.py:38-48](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_quiz_generator.py#L38-L48), [ai_flashcard_generator.py:31-39](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_flashcard_generator.py#L31-L39), [ai_study_plan.py:28-36](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_study_plan.py#L28-L36) | All three AI generators parse JSON by stripping markdown code fences with string splitting. If Gemini outputs malformed JSON → **silent empty return** (`return []` or `{"overview": "error"}`). No structured output / `response_schema` used. | Use `response_mime_type="application/json"` + `response_schema` like the OCR provider does |
| 8 | **High** | [ai_service.py:72-79](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_service.py#L72-L79) | Tutor generation does NOT use structured output. Gemini can return hallucinated page references, invented formulas, or non-chemistry content. The system prompt constrains behavior but is not enforced. | Add response validation; cross-check cited page numbers against retrieved chunks |
| 9 | **High** | No file | **No Redis cache invalidation after ingestion.** After a new PDF is ingested, old cache entries remain for up to 1 hour. | Add `POST /admin/rag/cache/clear` endpoint; auto-invalidate after ingestion completes |
| 10 | **Medium** | [rag.py:350](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py#L350) | Hybrid score formula: `blended = 0.35*vector + 0.65*lexical`. The heavy lexical weight means **real Gemini embeddings are underweighted** once they replace the hash fallback. | Re-tune weights when Gemini embeddings go live; add config settings for weights |
| 11 | **Medium** | [chat_service.py:39](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chat_service.py#L39) | `_MIN_BOOK_GROUNDED_CONFIDENCE = 0.25` is deliberately lowered for hash-based embeddings. Comment says to raise to 0.45-0.55. If production uses real embeddings, this is too permissive. | Make configurable via `settings`; raise before production |
| 12 | **Medium** | [ingestion_pipeline.py:498-515](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ingestion_pipeline.py#L498-L515) | `run_full_ingestion()` uses a **synchronous** `Session` but calls `await embed_batch()` and `await _extract_page()`. This works because it runs in a FastAPI `BackgroundTasks` context, but the sync session is shared across async calls. | Migrate to fully async session or use `run_in_executor()` |
| 13 | **Medium** | [homework_service.py:31-44](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/homework_service.py#L31-L44) | `solve_image()` takes a server-side `image_path` string. No multipart upload support. User must somehow place the image on the server first. | Add multipart upload endpoint |
| 14 | **Medium** | [gemini_provider.py:270-277](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L270-L277) | PDF upload polling uses `time.sleep(2)` in a `to_thread` block — 30 iterations × 2s = max 60s blocking. If the file never activates, this blocks a thread pool thread for a full minute. | Add a timeout parameter; use exponential backoff |
| 15 | **Medium** | [alembic/versions/](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/alembic/versions) | Only 1 migration file (`0001_initial_schema.py`). No migration for pgvector extension, IVFFlat index, or newer tables (ingestion_jobs, ingestion_pages). | Generate proper Alembic migrations for all tables |
| 16 | **Low** | [config.py:21-24](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/core/config.py#L21-L24) | Model names are configurable via environment but **defaults are hardcoded**. Model deprecation would require a code deploy. | Document model lifecycle; add model validation on startup |
| 17 | **Low** | [rag.py:23](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py#L23) | In-memory `_CACHE` dict is declared but **never actually used** — only Redis cache is used. Dead code. | Remove `_CACHE` dict |
| 18 | **Low** | [workers/ingestion_tasks.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/workers/ingestion_tasks.py) vs [ingestion/routes.py:180](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L180) | Celery `ingest_pdf` task exists but the `start` route uses FastAPI `BackgroundTasks` instead. Celery path is unused. | Either remove Celery task or add a route option to dispatch via Celery |

---

## 9. Recommended Implementation Plan

### P0 — Must fix before production

| Step | Action | Files |
|------|--------|-------|
| 1 | **Fix sync/async session mismatch** in `test-query` and `test-chunk` ingestion routes | `app/api/ingestion/routes.py` |
| 2 | **Implement retry-page** to actually re-run `_extract_page()` + `_store_page_chunks()` | `app/api/ingestion/routes.py` |
| 3 | **Add multipart PDF upload** endpoint | New: `app/api/ingestion/upload.py` |
| 4 | **Add cache invalidation** after ingestion and as an admin endpoint | `app/services/rag.py`, new route |
| 5 | **Raise `_MIN_BOOK_GROUNDED_CONFIDENCE`** to 0.45+ once real Gemini embeddings are deployed | `app/services/chat_service.py` |
| 6 | **Re-tune hybrid score weights** (0.35 vector / 0.65 lexical) for real embeddings | `app/services/rag.py` |
| 7 | **Add ingestion job cancellation** endpoint | `app/api/ingestion/routes.py` |

### P1 — Important for reliable RAG

| Step | Action | Files |
|------|--------|-------|
| 8 | **Wire AI quiz/flashcard/study-plan generators** to API routes | `app/api/quizzes.py`, `app/api/flashcards.py`, `app/api/study_plans.py` |
| 9 | **Use structured JSON mode** for quiz/flashcard/study-plan generation | `app/services/ai_quiz_generator.py`, `ai_flashcard_generator.py`, `ai_study_plan.py` |
| 10 | **Add RAG debug endpoint** exposing vector/lexical/hybrid scores per candidate | New: `app/api/rag/debug.py` |
| 11 | **Add RAG evaluation endpoint** with golden question set | New: `app/api/rag/evaluate.py` |
| 12 | **Add chunk inspect/edit/delete** endpoints | New: `app/api/admin/chunks.py` |
| 13 | **Add reindex endpoint** for re-embedding changed chunks | New: `app/api/admin/reindex.py` |
| 14 | **Generate Alembic migrations** for all current tables | `alembic/versions/` |
| 15 | **Add RAG feedback collection** endpoint | New: `app/api/rag/feedback.py` |

### P2 — Improvement / Observability

| Step | Action | Files |
|------|--------|-------|
| 16 | **Add streaming chat** (SSE) endpoint | New: `app/api/chat/stream.py` |
| 17 | **Add AI usage/cost monitoring** endpoint | New: `app/api/admin/ai_usage.py` |
| 18 | **Add AI capabilities** endpoint | New: `app/api/ai/capabilities.py` |
| 19 | **Remove dead code**: unused `_CACHE` dict, `TextbookChunk` (or mark deprecated) | `app/services/rag.py`, `app/models/textbook.py` |
| 20 | **Resolve Celery vs BackgroundTasks** — pick one pattern | `app/workers/`, `app/api/ingestion/routes.py` |

---

## 10. Exact Files to Modify

### Must Modify

| File | What to Change |
|------|----------------|
| [app/api/ingestion/routes.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py) | Fix `test-query`/`test-chunk` async session; implement real `retry-page`; add job cancel; add PDF upload |
| [app/services/rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py) | Add cache invalidation function; make hybrid weights configurable; remove dead `_CACHE` dict |
| [app/services/chat_service.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chat_service.py) | Make `_MIN_BOOK_GROUNDED_CONFIDENCE` configurable via settings |
| [app/core/config.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/core/config.py) | Add settings for `min_book_confidence`, `hybrid_vector_weight`, `hybrid_lexical_weight` |
| [app/services/ai_quiz_generator.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_quiz_generator.py) | Use structured JSON mode; add proper error handling |
| [app/services/ai_flashcard_generator.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_flashcard_generator.py) | Same as above |
| [app/services/ai_study_plan.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_study_plan.py) | Same as above |
| [app/api/quizzes.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/quizzes.py) | Add AI generation route |
| [app/api/flashcards.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/flashcards.py) | Add AI generation route |
| [app/api/study_plans.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/study_plans.py) | Add AI generation route |

### Must Create

| File | Purpose |
|------|---------|
| `app/api/rag/debug.py` | RAG debug endpoint with full scoring breakdown |
| `app/api/rag/evaluate.py` | RAG evaluation with golden questions |
| `app/api/rag/feedback.py` | User feedback on RAG answers |
| `app/api/admin/chunks.py` | Chunk inspect/edit/delete/approve |
| `app/api/admin/reindex.py` | Re-embed chunks for a source |
| `app/api/admin/cache.py` | Redis cache clear endpoint |
| `app/api/chat/stream.py` | SSE streaming chat endpoint |
| `alembic/versions/0002_*.py` | Proper migration for pgvector + all new tables |

### Consider Removing/Deprecating

| File | Reason |
|------|--------|
| [app/models/textbook.py:22-38](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L22-L38) (`TextbookChunk`) | Legacy table, not used by current RAG pipeline |
| [app/workers/ingestion_tasks.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/workers/ingestion_tasks.py) | Celery task exists but is never dispatched |
