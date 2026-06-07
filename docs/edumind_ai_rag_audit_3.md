# EduMind AI/RAG Codebase Audit

## 1. Executive Summary

This document presents a deep architectural audit of the **EduMind** backend codebase, specifically inspecting the implemented state of all AI, RAG, ingestion, database models, and service layers, and identifying architecture gaps.

### Summary of Implementation Status
*   **Fully Implemented**: 
    *   **Core RAG Retrieval & Hybrid Scoring**: Highly developed Arabic lexical normalizer, query cleaner, term expansion, and intent-based reranking. Implemented with PostgreSQL/pgvector (`vector_cosine_ops`) and an asynchronous SQLite Python-based similarity fallback for local development.
    *   **OCR / Page Ingestion Pipeline**: Full pipeline classifying pages into `SELECTABLE_TEXT`, `NEEDS_VISION`, and `MIXED_VISION`. Integrates Gemini Files API (uploading PDF once, extracting pages from PDF URI) with image rendering fallback at 300 DPI. Strict JSON output mode mapped to a Pydantic page extraction model.
    *   **Tutor Chat & Stateless Ask**: Multi-turn conversation sessions and one-off stateless questions with intent routing, approved chemistry dictionary lookup, chemical equation matching, and deterministic local fallback when Gemini is rate-limited or offline.
    *   **Homework Solver**: Solver routes for both text and image homework. Image-based homework uses the Gemini OCR provider for problem extraction before solving.
*   **Partially Implemented**:
    *   **Ingestion Status & Jobs**: Persisted in the database, but the API router reads/updates an in-memory dictionary (`_TASKS`), meaning job statuses are lost on server restarts.
    *   **Celery Worker Integration**: Celery is initialized and an ingestion task exists, but the ingestion router enqueues jobs using FastAPI’s synchronous in-process `BackgroundTasks` instead of Celery.
    *   **Redis Caching**: Redis client utilities exist, and the RAG service attempts to cache retrieved chunks, but the Redis connection in `chat_service.py` is closed per call, and rate-limiting/monitoring is not unified.
    *   **Retry Page Endpoint**: The route `POST /admin/ingestion/retry-page/{page_id}` only modifies the DB status to `queued_retry` and returns a stub message: *"Full per-page retry worker is not implemented yet."*
*   **Missing (Dead Code or Lacking API Routes)**:
    *   **AI Quiz, Flashcard & Study Plan Generators**: While the backend has services for generating questions (`ai_quiz_generator.py`), flashcards (`ai_flashcard_generator.py`), and study plans (`ai_study_plan.py`), **none of these services are wired to API endpoints**. The active quiz and study plan endpoints are entirely manual and read/write raw user data, completely bypassing Gemini.
    *   **Rich Citations & Citations Persistency**: Chat messages in the database do not persist sources, pages, or RAG diagnostics, preventing citation auditing or performance monitoring.
    *   **Spaced Repetition & Spaced Learning Generation**: The Leitner/SM-2 flashcard model columns exist, but no AI generation or automated scheduling API is available.

---

## 2. External AI API Call Map

The following table documents all external AI calls found in the codebase. All Google GenAI calls are synchronous and wrapped inside `asyncio.to_thread`.

| Service | File | Function | Model | API Method | Input | Output | Validation | Fallback | Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Conversational Chat & Ask Tutor** | [ai_service.py:L59](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_service.py#L59) | `get_ai_response` | `settings.model_name` (`gemini-3.5-flash`) | `client.models.generate_content` | List of `Content` messages, system instruction | `response.text` (str) | None (Reads raw text) | Catches errors & returns Arabic quota error or offline message; `chat_service.py` falls back to `_local_rag_answer` | Hallucination if RAG context is weak; malformed formatting. |
| **Document Embedding** | [embeddings.py:L113](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L113) & [L126](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L126) | `_embed_gemini_one` / `_embed_gemini_batch` | `settings.gemini_embedding_model` (`gemini-embedding-001`) | `client.models.embed_content` | Passage string or list of strings; `task_type="RETRIEVAL_DOCUMENT"` | List of `768-dim` floats | Length check matches input | Local multilingual `SentenceTransformer` or local token-SHA256 mock hashing | Disables Gemini embeddings on failure, causing silent degradations to lower-quality hashing. |
| **Query Embedding** | [embeddings.py:L113](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L113) | `_embed_one` (via `embed_query`) | `settings.gemini_embedding_model` (`gemini-embedding-001`) | `client.models.embed_content` | Query string; `task_type="RETRIEVAL_QUERY"` | List of `768-dim` floats | None | Local multilingual `SentenceTransformer` or local token-SHA256 mock hashing | Divergence from document embeddings if fallbacks trigger mismatching vector spaces. |
| **Primary Page OCR** | [gemini_provider.py:L298](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L298) | `extract_page_from_pdf` | `settings.gemini_document_model` (`gemini-3.5-flash`) | `client.models.generate_content` | Gemini PDF file handle URI, prompt, structured JSON schema | Pydantic model (`PageExtractionResult`) | Strict Pydantic response schema; quality checks (Arabic ratio, char counts) | Falls back to `gemini_document_fallback_model` (e.g. `gemini-2.5-pro`, `gemini-2.5-flash-lite`); falls back to 300 DPI rendered image | Schema parsing errors or low-quality Arabic OCR. |
| **Fallback OCR (Image-based)** | [gemini_provider.py:L339](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L339) | `extract_page` | `settings.gemini_document_model` (`gemini-3.5-flash`) | `client.models.generate_content` | Page image bytes (PNG), prompt, structured JSON schema | Pydantic model (`PageExtractionResult`) | Strict Pydantic response schema; quality checks (Arabic ratio, char counts) | Fallback model in routing list; wraps raw text as a mixed section on parsing failure | Render latency (300 DPI conversion); token consumption for large images. |
| **PDF Single Upload** | [gemini_provider.py:L250](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L250) | `upload_pdf` | None | `client.files.upload` | Local PDF file path, mimetype | `UploadedDocument` (includes URI and remote name) | Polls file state until `ACTIVE` or `FAILED` | Falls back to image rendering for all pages | PDF size limits; Files API upload timeouts. |
| **Quiz MCQ Generator (Unused)** | [ai_quiz_generator.py:L9](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_quiz_generator.py#L9) | `generate_questions_for_topic` | `settings.model_name` (`gemini-3.5-flash`) | `generate_content` (via `ai_service`) | Prompt requesting JSON format, RAG topic context | JSON string (parsed with `json.loads`) | Strip code fences; fallback to `[]` on failure | Returns `[]` | No schema enforcement in Gemini config; high risk of malformed JSON or parsing crash. |
| **Flashcard Generator (Unused)** | [ai_flashcard_generator.py:L7](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_flashcard_generator.py#L7) | `generate_flashcards_for_topic` | `settings.model_name` (`gemini-3.5-flash`) | `generate_content` (via `ai_service`) | Prompt requesting JSON format, RAG topic context | JSON string (parsed with `json.loads`) | Strip code fences; fallback to `[]` on failure | Returns `[]` | **Critical runtime bug**: tries to instantiate `Flashcard` with invalid parameters (`front`, `back`, `hint`). |
| **Study Plan Generator (Unused)** | [ai_study_plan.py:L7](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_study_plan.py#L7) | `generate_study_plan` | `settings.model_name` (`gemini-3.5-flash`) | `generate_content` (via `ai_service`) | Prompt requesting JSON format, exam target date, topics | JSON string (parsed with `json.loads`) | Strip code fences; fallback to default dict | Returns default dict | No schema enforcement in Gemini config; risk of model ignoring output constraints. |

---

## 3. Implemented AI/RAG Backend APIs

The table below catalogs all AI/RAG-related endpoints found in the codebase.

| Method | Path | Purpose | Auth | Request Schema | Response Schema | File Path | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/api/v1/chat/sessions` | Create a new chat session | User | `SessionCreate` | `SessionResponse` | [chat/routes.py:L25](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L25) | Implemented |
| **GET** | `/api/v1/chat/sessions` | List chat sessions for a user | User | None | `list[SessionResponse]` | [chat/routes.py:L40](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L40) | Implemented |
| **GET** | `/api/v1/chat/sessions/{session_id}` | Retrieve chat session messages | User | None | `SessionResponse` | [chat/routes.py:L48](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L48) | Implemented |
| **POST** | `/api/v1/chat/sessions/{session_id}/messages` | Send message in chat session (generates RAG reply) | User | `SendMessageRequest` | `MessageResponse` | [chat/routes.py:L57](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L57) | Implemented |
| **POST** | `/api/v1/chat/ask` | Stateless RAG tutor ask | User | `ChatAskRequest` | `ChatAnswerResponse` | [chat/routes.py:L73](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L73) | Implemented |
| **POST** | `/api/v1/chat/messages/{message_id}/feedback` | Send user rating for tutor message | User | `MessageFeedbackRequest` | `MessageResponse` | [chat/routes.py:L123](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L123) | Implemented |
| **DELETE** | `/api/v1/chat/sessions/{session_id}` | Delete chat session | User | None | None | [chat/routes.py:L133](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/chat/routes.py#L133) | Implemented |
| **GET** | `/api/v1/rag/search` | Search chunks (query params) | User | None | `list[RetrievedChunkResponse]` | [rag/routes.py:L31](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/rag/routes.py#L31) | Implemented |
| **POST** | `/api/v1/rag/retrieve` | Retrieve matching RAG chunks | User | `RagRetrieveRequest` | `RagRetrieveResponse` | [rag/routes.py:L59](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/rag/routes.py#L59) | Implemented |
| **POST** | `/api/v1/rag/retrieve-debug` | Retrieve chunks with diagnostics | User | `RagRetrieveRequest` | `RagRetrieveDebugResponse` | [rag/routes.py:L81](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/rag/routes.py#L81) | Implemented |
| **POST** | `/api/v1/homework/solve-text` | Solve a textbook problem as text | User | `HomeworkSolveTextRequest` | `HomeworkResponse` | [homework.py:L14](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/homework.py#L14) | Implemented |
| **POST** | `/api/v1/homework/solve-image` | Solve homework from rendered image path | User | `HomeworkSolveImageRequest` | `HomeworkResponse` | [homework.py:L23](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/homework.py#L23) | Implemented |
| **GET** | `/api/v1/homework/history` | List solved homework items | User | None | `list[HomeworkResponse]` | [homework.py:L32](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/homework.py#L32) | Implemented |
| **GET** | `/api/v1/homework/{homework_id}` | Get homework item solution details | User | None | `HomeworkResponse` | [homework.py:L37](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/homework.py#L37) | Implemented |
| **POST** | `/api/v1/quizzes/generate` | Generate questions for topic (seeds database lookup) | None | `QuizGenerateRequest` | `QuizGenerateResponse` | [quizzes.py:L22](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/quizzes.py#L22) | **No AI call**. Pulls seeded questions. |
| **POST** | `/api/v1/quizzes/submit` | Submit graded answers and update weak topics | User | `QuizSubmitRequest` | `QuizSubmitResponse` | [quizzes.py:L41](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/quizzes.py#L41) | Implemented |
| **GET** | `/api/v1/quizzes/history` | List quiz attempt history | User | None | `list[QuizAttemptResponse]` | [quizzes.py:L56](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/quizzes.py#L56) | Implemented |
| **GET** | `/api/v1/quizzes/recommendations` | Get topics to study based on progress | None | None | `list[QuizRecommendationResponse]` | [quizzes.py:L61](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/quizzes.py#L61) | Implemented |
| **GET** | `/api/v1/flashcards` | List flashcards (optionally by topic) | None | None | `list[FlashcardResponse]` | [flashcards.py:L19](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/flashcards.py#L19) | Implemented |
| **POST** | `/api/v1/flashcards` | Create new flashcard manually | Admin | `FlashcardCreateRequest` | `FlashcardResponse` | [flashcards.py:L24](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/flashcards.py#L24) | Implemented |
| **POST** | `/api/v1/flashcards/{flashcard_id}/review` | Submit spaced learning repetition score | User | `FlashcardReviewRequest` | `FlashcardProgressResponse` | [flashcards.py:L33](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/flashcards.py#L33) | Implemented |
| **POST** | `/api/v1/study-plans` | Create a new study plan manually | User | `StudyPlanCreate` | `StudyPlanResponse` | [study_plans.py:L25](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/study_plans.py#L25) | **No AI call**. Takes plan JSON. |
| **GET** | `/api/v1/study-plans` | List user study plans | User | None | `list[StudyPlanResponse]` | [study_plans.py:L10](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/study_plans.py#L10) | Implemented |
| **POST** | `/api/v1/admin/ingestion/sources` | Register a new content source | Admin | `SourceRegisterRequest` | `SourceResponse` | [ingestion/routes.py:L236](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L236) | Implemented |
| **POST** | `/api/v1/admin/ingestion/start` | Trigger background document ingestion | Admin | `IngestionStartRequest` | `IngestionStartResponse` | [ingestion/routes.py:L172](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L172) | Implemented (In-process background task) |
| **GET** | `/api/v1/admin/ingestion/status/{task_id}`| Get ingestion status from memory | Admin | None | `IngestionStatusResponse` | [ingestion/routes.py:L271](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L271) | Implemented (Volatility risk) |
| **GET** | `/api/v1/admin/ingestion/sources` | List all registered sources | Admin | None | `list[SourceResponse]` | [ingestion/routes.py:L228](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L228) | Implemented |
| **GET** | `/api/v1/admin/ingestion/stats` | Retrieve database and chunk statistics | Admin | None | `IngestionStatsResponse` | [ingestion/routes.py:L279](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L279) | Implemented |
| **DELETE** | `/api/v1/admin/ingestion/clear` | Clear all chunks from database | Admin | None | `IngestionClearResponse` | [ingestion/routes.py:L323](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L323) | Implemented |
| **DELETE** | `/api/v1/admin/ingestion/source/{source_id}`| Delete source, chunks, and questions | Admin | None | `SourceDeleteResponse` | [ingestion/routes.py:L333](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L333) | Implemented |
| **GET** | `/api/v1/admin/ingestion/pages/{source_id}` | List page extraction details | Admin | None | `list[IngestionPageResponse]` | [ingestion/routes.py:L362](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L362) | Implemented |
| **POST** | `/api/v1/admin/ingestion/retry-page/{page_id}`| Mark an ingestion page for retry | Admin | None | `IngestionRetryPageResponse` | [ingestion/routes.py:L376](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L376) | **Stub/Partial** (No worker) |
| **POST** | `/api/v1/admin/ingestion/test-query` | Run retrieval debug query | Admin | `IngestionTestQueryRequest` | `IngestionTestQueryResponse` | [ingestion/routes.py:L394](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L394) | Implemented |
| **POST** | `/api/v1/admin/ingestion/test-chunk/{chunk_id}`| Retrieve chunks similar to a chunk | Admin | None | `TestChunkResponse` | [ingestion/routes.py:L418](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L418) | Implemented |
| **GET** | `/api/v1/admin/ingestion/questions/unreviewed`| List extracted questions requiring review | Admin | None | `list[ExtractedQuestionResponse]` | [ingestion/routes.py:L455](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/questions/unreviewed) | Implemented |
| **POST** | `/api/v1/admin/ingestion/questions/{question_id}/review`| Approve or modify extracted questions | Admin | `QuestionReviewRequest` | `ExtractedQuestionResponse` | [ingestion/routes.py:L470](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L470) | Implemented |
| **POST** | `/api/v1/admin/ingestion/rebuild-from-cache` | Rebuild chunks from locally cached page JSONs | Admin | `IngestionRebuildCacheRequest`| `IngestionRebuildCacheResponse`| [ingestion/routes.py:L205](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L205) | Implemented |

---

## 4. RAG Retrieval Implementation

The RAG retrieval engine in [rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py) uses a hybrid retrieval pipeline that blends semantic vector search with Arabic lexical matching.

### 1. Hybrid Scoring Formula
For each chunk, the base hybrid score is calculated as follows:
*   If `lexical_score <= 0`, the blended score is just `vector_score`.
*   Otherwise, the blended score is:
    $$\text{Blended Score} = 0.35 \times \text{Vector Score} + 0.65 \times \text{Lexical Score}$$
*   The final score is selected as:
    $$\text{Base Score} = \max(\text{Blended Score}, \text{Lexical Score}, \text{Vector Score})$$

### 2. Intent-Based Reranking Adjustments
Depending on the classified query intent, the RAG engine adjusts the score:
*   **Definition Lookup**:
    *   `+0.18` boost for chunk type `"definition"` or `"concept"`.
    *   `+0.16` boost if content matches definition patterns like `"مواد تعطي"`.
    *   `-0.32` penalty for chunks classified as `"objectives"`.
    *   `-0.42` penalty if base chemistry questions do not contain base markers (`"هيدروكسيد"`, `"oh-"`).
*   **Reaction/Equation Lookup**:
    *   `+0.18` boost for chunk type `"equation"` or `"activity"`.
    *   `-0.10` penalty for `"definition"` chunks.
*   **Chemical Entity Match**:
    *   `+0.08` boost per overlapping chemical formula (e.g., `CaO`, `H2O`) up to `+0.24`.

### 3. Arabic Text Normalization
To prevent noisy OCR artifacts from breaking matches, both the query and textbook content are normalized:
*   **Diacritics**: Removed using regex `[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]`.
*   **Alef**: `أ`, `إ`, `آ`, `ٱ` normalized to `ا`.
*   **Yaa & Taa**: `ؤ` -> `و`, `ئ` -> `ي`, `ى` -> `ي`, `ة` -> `ه`.
*   **Chemistry Subscripts**: Subscript numerals (`₂`, `₄`, `₃`) are flattened to standard digits (`2`, `4`, `3`) to ensure equivalence in formulas.

### 4. Redis Cache Integration
RAG results are cached in Redis. The key is built using a version prefix and an MD5 hash of the request parameters:
$$\text{Key} = \text{"rag\_cache:v13:"} + \text{MD5(query | user\_id | filters | top\_k | intent)}$$
*   **TTL**: 3,600 seconds (1 hour).
*   **Cache Content**: JSON-serialized list of dictionaries containing retrieved chunks.

---

## 5. OCR / Document Ingestion Implementation

The document ingestion pipeline processes Syrian curriculum PDFs using a combination of local structural classification and multimodal extraction.

### 1. Ingestion Steps
1.  **Page Classification**: Uses PyMuPDF and pdfplumber to check image area ratio and character counts. If characters are $< 50$, the page is labeled `NEEDS_VISION`. If image area ratio is $\ge 15\%$ or tables exist, it is labeled `MIXED_VISION`. Otherwise, it is `SELECTABLE_TEXT`.
2.  **PDF Upload**: The PDF is uploaded once using `client.files.upload` to keep token costs low.
3.  **Structured Extraction**: For vision pages, Gemini is called with `PageExtractionResult` response schema. Prompt instructions enforce preserving chemical formulas (`H2O`, `CO2`), Arabic spelling, table markdown structures, and diagram descriptions.
4.  **DPI Image Fallback**: If PDF-based extraction returns low-quality markers (e.g. Arabic char ratio $< 20\%$ or character count $< 40$), the page is rendered as a 300 DPI PNG file locally, and the image bytes are sent to Gemini for OCR extraction.
5.  **Chunking**: Chunks are split by section, keeping tables, diagrams, and equations atomic.
6.  **Embedding & Storage**: Embeddings are generated in batches of 100 using `gemini-embedding-001` and saved to `rag_chunks` alongside extracted questions saved to `extracted_questions`.

---

## 6. Database Model Verification

This section verifies the SQLAlchemy models defined in `backend/app/models/` against the documented architecture.

| Model | Table | Important Columns | Relationships | Indexes | Issues Found |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ContentSource** | `content_sources` | `id` (PK), `source_type`, `title`, `file_path`, `status` | `chunks` (RagChunk), `extracted_questions` (ExtractedQuestion) | `id`, `source_type`, `status` | **ERD Discrepancy**: This table is completely missing from the ERD documentation. |
| **RagChunk** | `rag_chunks` | `id` (PK), `source_id` (FK), `chapter_id`/`lesson_id`/`topic_id` (FK, nullable), `page_number`, `content`, `embedding` (`VECTOR(768)`) | `source` (ContentSource), `chapter`, `lesson`, `topic` | `source_id`, `chapter_id`, `lesson_id`, `topic_id`, `page_number`, `content_type`, `source_type`, `embedding` (ivfflat) | **ERD Discrepancy**: This table is missing from the ERD documentation. The ERD documents a legacy `TEXTBOOK_CHUNKS` table instead. |
| **ExtractedQuestion** | `extracted_questions` | `id` (PK), `source_id` (FK), `question_text`, `options` (JSON), `correct_answer`, `needs_review` | `source` (ContentSource), `topic` | `source_id`, `chapter_id`, `topic_id`, `needs_review` | **ERD Discrepancy**: This table is missing from the ERD documentation. |
| **IngestionJob** | `ingestion_jobs` | `id` (PK), `job_uid`, `source_id` (FK), `status`, `progress`, `result_json`, `errors_json` | `source` (ContentSource) | `id`, `job_uid`, `source_id`, `status` | **ERD Discrepancy**: This table is missing from the ERD documentation. |
| **IngestionPage** | `ingestion_pages` | `id` (PK), `source_id` (FK), `page_number`, `page_type`, `status`, `completeness_score` | `source` (ContentSource), `job` (IngestionJob) | `id`, `source_id`, `page_number`, `status` | **ERD Discrepancy**: This table is missing from the ERD documentation. |
| **Homework** | `homework` | `id` (PK), `user_id` (FK), `problem_text`, `solution`, `image_url`, `extracted_text`, `source_chunks` (JSON), `confidence_score` | `user`, `topic` | `id`, `user_id`, `topic_id` | **ERD Discrepancy**: ERD lacks columns `image_url`, `extracted_text`, `source_chunks`, and `confidence_score`. |
| **Flashcard** | `flashcards` | `id` (PK), `topic_id` (FK), `front_ar`, `back_ar`, `created_by` | `topic`, `progress_records` (FlashcardProgress) | `id`, `topic_id` | None. Matches ERD. |
| **FlashcardProgress** | `flashcard_progress` | `id` (PK), `user_id` (FK), `flashcard_id` (FK), `mastered`, `ease_factor`, `interval_days`, `next_review_at` | `user`, `flashcard` | `id`, `user_id`, `flashcard_id` | **ERD Discrepancy**: ERD lacks Leitner columns `ease_factor`, `interval_days`, and `next_review_at`. |
| **ChatSession** | `chat_sessions` | `id` (PK), `user_id` (FK), `lesson_id` (FK, nullable), `title`, `style` | `user`, `messages` (ChatMessage) | `id`, `user_id`, `lesson_id` | None. Matches ERD. |
| **ChatMessage** | `chat_messages` | `id` (PK), `session_id` (FK), `role`, `content`, `format`, `feedback`, `latency_ms` | `session` (ChatSession) | `id`, `session_id` | **Citations Gap**: Lacks columns to save retrieved RAG sources, pages, or confidence. |

---

## 7. Missing APIs to Implement

The following routes are recommended for production readiness, ordered by priority.

| Priority | API Name | Method / Path | Why Needed | Suggested Request JSON | Suggested Response JSON |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0** | **Upload PDF Source File** | `POST /api/v1/admin/ingestion/upload` | Multipart upload for textbooks so PDFs do not need to be manually pre-positioned on the server path. | Form-data: `file: File`, `source_type: string` | `{"file_path": "data/uploads/chemistry.pdf", "filename": "chemistry.pdf"}` |
| **P0** | **AI Flashcard Generator** | `POST /api/v1/flashcards/generate` | Triggers the implemented `ai_flashcard_generator` and saves cards to the database. | `{"topic_id": 5, "limit": 5}` | `{"flashcards_created": 5, "topic_id": 5}` |
| **P0** | **AI Study Plan Generator** | `POST /api/v1/study-plans/generate` | Triggers the implemented `ai_study_plan` generator for target exam dates. | `{"target_date": "2026-06-30", "topics": ["الحموض", "الأسس"]}` | `{"plan_id": 1, "status": "active", "weeks_count": 4}` |
| **P1** | **RAG Debug Reranker** | `POST /api/v1/rag/debug-rerank` | Detailed breakdown of vector, lexical, and intent scores for RAG troubleshooting. | `{"query": "ما هي الحموض؟", "top_k": 3}` | `{"query": "ما هي الحموض؟", "candidates": [{"chunk_id": 1, "vector_score": 0.45, "lexical_score": 0.8, "hybrid_score": 0.72, "reasons": ["exact_formula"]}]}` |
| **P1** | **Cost & Latency Monitor** | `GET /api/v1/admin/ai/monitoring` | Tracks LLM token usage, provider latencies, and billing costs. | None | `{"calls_total": 1250, "token_count": 4850000, "estimated_cost_usd": 12.12, "avg_latency_ms": 1150}` |
| **P2** | **Citation Citator** | `GET /api/v1/chat/messages/{message_id}/citations` | Validates sources and retrieves the corresponding text chunk page images. | None | `{"message_id": 10, "citations": [{"chunk_id": 50, "page": 11, "preview": "...", "source_title": "Syrian Chemistry Textbook"}]}` |

---

## 8. Bugs / Risks / Inconsistencies

The table below lists concrete issues identified in the codebase.

| Severity | File Path | Evidence | Recommended Fix |
| :--- | :--- | :--- | :--- |
| **Critical** | [ai_flashcard_generator.py:L43-47](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_flashcard_generator.py#L43-47) | Instantiates the `Flashcard` model with columns `front`, `back`, and `hint`. However, [flashcard.py:L19-20](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/flashcard.py#L19-20) defines the database columns as `front_ar` and `back_ar` and has no `hint` column. This will cause a runtime crash. | Modify [ai_flashcard_generator.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_flashcard_generator.py) to map `front` to `front_ar`, `back` to `back_ar`, and remove `hint` or serialize it into `metadata_json`. |
| **High** | [routes.py:L40](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L40) | Ingestion status reads from an in-memory dictionary `_TASKS`. Server restarts will wipe all visible ingestion progress, even though the database tables (`ingestion_jobs`, `ingestion_pages`) contain the records. | Rewrite the status endpoints to query `ingestion_jobs` and `ingestion_pages` tables. |
| **High** | [routes.py:L172](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L172) | Ingestion is triggered via FastAPI `BackgroundTasks`. This executes in the FastAPI main thread pool, which can lead to event-loop blocking during large PDF extractions. Celery tasks are defined in `workers/ingestion_tasks.py` but are never dispatched. | Change `background_tasks.add_task` in `routes.py` to `ingest_pdf_task.delay` to dispatch to the Celery worker queue. |
| **Medium** | [gemini_client.py:L110](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/gemini_client.py#L110) | Gemini model requests do not specify retry configurations, except in `document_generation_config`. General tutor generation and embeddings will fail immediately on transient rate-limiting errors. | Apply `generation_http_options()` containing `HttpRetryOptions(attempts=5)` to all Gemini configurations, including embeddings. |
| **Medium** | [routes.py:L376](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py#L376) | The retry page route returns a static stub message and does not actually retry page ingestion or recalculate chunk records. | Implement a Celery retry task that re-extracts the single page, deletes old chunks for that page, and embeds the new ones. |
| **Medium** | [routes.py:L23](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/quizzes.py#L23) & [routes.py:L25](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/study_plans.py#L25) | Desired AI generation routes for Quizzes and Study Plans bypass their respective AI generator services and rely on manual request parameters. | Add AI routes such as `/quizzes/generate-ai` and `/study-plans/generate-ai` that call the corresponding generator services. |

---

## 9. Recommended Implementation Plan

### Phase P0 — Critical System Reliability & API Integrity
1.  **Fix Flashcard Schema Mismatch**: Update [ai_flashcard_generator.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_flashcard_generator.py) to map `front` to `front_ar` and `back` to `back_ar` to prevent runtime crashes.
2.  **Add AI Generation Endpoints**: Create Pydantic schemas and add FastAPI routers to expose:
    *   `POST /api/v1/flashcards/generate` (calls `generate_flashcards_for_topic`)
    *   `POST /api/v1/study-plans/generate` (calls `generate_study_plan`)
    *   `POST /api/v1/quizzes/generate-ai` (calls `generate_questions_for_topic`)
3.  **Migrate Ingestion to Celery**: Change `BackgroundTasks` to Celery `delay()` enqueues in `api/ingestion/routes.py` to prevent server resource starvation.

### Phase P1 — Observability, Quality Gates & Caching
1.  **Durable Ingestion Tracking**: Modify [api/ingestion/routes.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/api/ingestion/routes.py) to write and poll ingestion job states from the `ingestion_jobs` database table rather than the volatile `_TASKS` memory map.
2.  **Unify Arabic Normalization**: Deprecate the lightweight normalizer in `chunking.py` and import the robust normalizer from `arabic_normalizer.py` across the ingestion pipeline to avoid retrieval drift.
3.  **Implement RAG Caching**: Configure the Redis client in `chat_service.py` and `rag.py` to reuse connections efficiently and verify that RAG results are retrieved from Redis cache.

### Phase P2 — Obsolescence & Observer Features
1.  **AI Cost & Latency Auditing**: Create an `ai_api_calls` database table to audit prompt/completion tokens, latency, and costs for all Gemini calls.
2.  **Homework Image Upload Flow**: Expose an endpoint that accepts image file uploads (multipart) and stores them in the local assets folder rather than accepting direct server paths.

---

## 10. Exact Files to Modify

*   **`backend/app/core/config.py`**: Add missing environment variables for upload directory configurations.
*   **`backend/app/services/ai_flashcard_generator.py`**: Correct database column assignments.
*   **`backend/app/api/ingestion/routes.py`**:
    *   Replace `BackgroundTasks` with Celery enqueuing.
    *   Deduplicate `_TASKS` logic by reading from the `ingestion_jobs` database table.
    *   Implement page retry task trigger.
*   **`backend/app/api/flashcards.py`**: Add the new AI generation endpoint.
*   **`backend/app/api/study_plans.py`**: Add the new AI generation endpoint.
*   **`backend/app/api/quizzes.py`**: Add the new AI generation endpoint.
*   **`backend/app/api/chat/routes.py`**: Update response model schemas to include citation block metadata.
*   **`backend/app/services/chat_service.py`**: Persist citation sources in `chat_messages` or related metadata tables.
*   **`backend/app/services/embeddings.py`**: Wrap embedding client requests with HTTP retry configs.
*   **`backend/app/services/ingestion_pipeline.py`**: Switch chunk normalization imports to `arabic_normalizer.py`.
