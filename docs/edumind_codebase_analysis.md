# EduMind Codebase Analysis — Architecture & Multimedia Integration Points

Date: 2026-06-12

Scope: backend architecture, database models, API routes, schemas, services, AI/RAG pipeline, OCR/document ingestion, multimedia hooks, Celery/Redis jobs, Swagger/Gemini readiness, chat history/memory behavior, and feature gaps.

Repository inspected:

```text
/Users/sereenkh/Github-Projects/edumind-team-06/src
```

The previous report in this file was stale in several places. This version reflects the current code under `src/backend`.

## 1. Executive Summary

The backend is a real FastAPI application, not only a prototype. It has a broad API surface, SQLAlchemy models, Alembic migrations, PostgreSQL/pgvector support, Redis/Celery wiring, Gemini integration through the modern `google-genai` SDK, RAG retrieval, semantic RAG, OCR/document ingestion, solution-book ingestion, chat sessions, homework solving, quizzes, flashcards, study plans, progress, and notifications.

Current backend maturity: medium. The core skeleton is production-oriented, but several parts are still incomplete or mixed between production and local-development behavior.

Swagger readiness: mostly ready. The app includes routers under `/api/v1`, so Swagger should expose the active APIs at `/docs` when the backend imports successfully. I verified key backend modules compile:

```bash
python -m py_compile app/api/ingestion/routes.py app/api/router.py app/main.py
```

AI/RAG readiness: partially ready. The system uses PostgreSQL/pgvector through `RagChunk.embedding`, has hybrid retrieval, semantic retrieval, Redis caching hooks, query rewriting, HyDE/multi-query logic, reranking support, and answer quality gates. However, embedding configuration is inconsistent with the stated expectation: code and `.env.example` currently use `gemini-embedding-001`, not `text-embedding-004`. Local semantic embedding fallback depends on `sentence-transformers`, but that dependency is commented out, so clean installs may fall back to deterministic hash embeddings.

OCR/document readiness: strong foundation. Production OCR uses Gemini direct PDF/document extraction through `google-genai`. No OCRArena production dependency was found. The ingestion pipeline handles selectable text, vision-needed pages, mixed pages, dry-run vs production rules, page caches, chunks, and extracted questions. The solution-book ingestion path is implemented and exposed through admin endpoints.

Main blockers:

- Notification reminders are modeled and scheduled in Celery config, but Docker starts only a Celery worker, not Celery Beat. Scheduled reminder delivery will not run automatically unless Beat is started separately.
- `/admin/ingestion/start` uses FastAPI `BackgroundTasks` plus in-memory `_TASKS`; jobs are not fully durable across backend restarts.
- `/chat/ask` is a one-shot endpoint and does not store new messages by default. Persistent chat history exists only through session endpoints.
- Multimedia output is mostly structured placeholders and routing. Text is real; image/page references are partly real; TTS/audio, generated image, video/reel, and interactive media pipelines are not fully implemented.
- Homework image solving accepts an `image_path`, not a mobile-friendly file upload.
- `chat_service.py` is very large and mixes routing, retrieval, prompt logic, dictionary rules, media routing, and local fallback logic.
- README still references OpenAI, while the backend uses Gemini/google-genai.

## 2. Repository Structure

Important backend folders and files found:

```text
src/
  backend/
    app/
      main.py
      database.py
      api/
        router.py
        auth/
        chat/
        chapters/
        lessons/
        topics/
        elements/
        ingestion/
        rag/
        study_plans/
        progress/
        quizzes/
        exams/
        homework/
        flashcards/
        health/
        notifications/
      core/
        config.py
        dependencies.py
        redis.py
        security.py
        middleware.py
      models/
        user.py
        student_profile.py
        chemistry.py
        textbook.py
        ingestion.py
        chat.py
        notification.py
        study_plan.py
        homework.py
        assessment.py
        flashcard.py
        user_progress.py
        achievement.py
        reel.py
        device.py
        interest.py
        topic.py
        billing.py
      schemas/
        auth.py
        chat.py
        rag.py
        ingestion.py
        notification.py
        homework.py
        quiz.py
        flashcards.py
        progress.py
        preferences.py
        common.py
      services/
        ai_service.py
        gemini_client.py
        chat_service.py
        rag.py
        semantic_rag.py
        embeddings.py
        ingestion_pipeline.py
        solution_book_ingestion.py
        rag_rebuild.py
        chunking.py
        homework_service.py
        notification_service.py
        reminder_service.py
        learning_mode_router.py
        tutor_prompt_builder.py
        ocr/
          base.py
          gemini_provider.py
          normalization.py
      workers/
        celery_app.py
        ingestion_tasks.py
        notification_tasks.py
    alembic/
      env.py
      versions/
    scripts/
    tests/
    data/
    .env.example
    requirements.txt
  frontend-web/
  docs/
  docker-compose.yml
```

Items requested but not present exactly as named:

- No `app/db/` package. Database setup is in `app/database.py`.
- No `app/tasks/` package. Background jobs are in `app/workers/`.
- No top-level `migrations/` folder. Alembic migrations are in `backend/alembic/`.
- No root `pyproject.toml` for the backend.
- `docker-compose.yml` is under `src/docker-compose.yml`, not repository root.

## 3. Backend Runtime Architecture

The backend entry point is `app/main.py`.

Runtime behavior:

- Creates a FastAPI app with title/version metadata and OpenAPI tags.
- Registers CORS from settings.
- Adds `RateLimitMiddleware`.
- Mounts textbook media under `/media/books`.
- Includes all API routes under `/api/v1`.
- Exposes a root health endpoint at `/health`.
- Initializes SQLite schema only for local SQLite URLs during lifespan.

Database setup is in `app/database.py`:

- Uses SQLAlchemy 2.0 declarative base.
- Provides sync engine/session: `engine`, `SessionLocal`, `get_db`.
- Provides async engine/session: `async_engine`, `AsyncSessionLocal`, `get_async_db`.
- Uses SQLite-specific JSON fallback behavior for local development.

Configuration is in `app/core/config.py`:

- Uses `pydantic-settings`.
- Defaults to PostgreSQL connection values.
- Auto-generates async database URL from sync URL when possible.
- Contains Gemini, ingestion, Redis, Celery, CORS, JWT, and admin settings.
- Validates `INGESTION_MODE` as only `dry_run` or `production`.

Docker setup:

- PostgreSQL is `pgvector/pgvector:pg16`.
- Redis is `redis:7-alpine`.
- Backend container runs migrations and starts Uvicorn.
- Celery worker container exists.
- No Celery Beat container is defined.

## 4. Database Models

### User And Profile

`User` is the central account model. It includes:

- Auth fields: email, password hash, active/admin flags.
- Legacy preference fields: `teaching_style`, `answer_format`.
- New preference fields: `teaching_level`, `explanation_method`, `learning_modes`, `student_interests`.
- Gamification fields: XP, level, streak.
- Relationships to profile, chat sessions, progress, quiz attempts, flashcards, study plans, homework, achievements, billing, devices, notifications, notification preferences, and reminder events.

`StudentProfile` stores:

- Grade/subject.
- Learning style and language.
- New tutor preferences.
- Goals and target exam date.
- Metadata JSON.

### Chemistry Curriculum

`Chapter` represents a large ordered unit in the chemistry book or curriculum.

`Lesson` represents an ordered instructional unit inside a chapter. Lessons have difficulty, duration, content, and progress relations.

`Topic` represents a conceptual tag such as acids, bases, concentration, hydrocarbons, or salts. Topics can cut across chapters/lessons and are used for quizzes, progress, flashcards, homework, extracted questions, and RAG tagging.

See section 13 for the recommended meaning of Chapter vs Lesson vs Topic.

### Progress And Learning

The backend includes:

- `LessonProgress`
- `UserProgress`
- `Achievement`
- `StudyPlan`
- `Flashcard`
- `FlashcardProgress`
- `Question`
- `QuizAttempt`
- `QuestionAttempt`
- `Homework`

These models support the expected education platform features, but some service/API behavior is still basic.

### Chat History

`ChatSession` and `ChatMessage` exist.

`ChatSession` stores:

- `user_id`
- optional `lesson_id`
- title/style
- ordered messages

`ChatMessage` stores:

- `session_id`
- role
- content
- format
- feedback
- media URL
- latency

This means persistent chat history exists for session-based chat.

### RAG And Ingestion

`ContentSource` represents uploaded or registered knowledge sources such as textbook, solution book, exams, notes, or answer keys.

`RagChunk` stores retrievable text chunks:

- source, chapter, lesson, topic references
- page number
- chunk index
- content and normalized content
- content type and source type
- extraction method
- language
- metadata JSON
- vector embedding

For PostgreSQL, `RagChunk.embedding` is `Vector(768)`. For SQLite/local mode, it falls back to JSON.

`ExtractedQuestion` stores question-bank style items extracted from sources.

`IngestionJob` and `IngestionPage` track ingestion status and per-page outcomes.

### Notifications

`Notification` stores in-app reminders and notification history:

- type
- title/message
- status: unread/read/archived
- priority
- scheduled/delivered/read timestamps
- action URL
- metadata

`NotificationPreference` stores reminder preferences:

- exam reminders
- lesson reminders
- push/email/in-app flags
- reminder time
- timezone

`ReminderEvent` stores scheduled reminder jobs:

- source type: exam/lesson
- source id
- reminder type
- scheduled time
- status
- notification id

There is a uniqueness constraint on user/source/reminder identity to avoid duplicate reminder events.

## 5. API Routes And Swagger Readiness

All main routers are included through:

```text
/api/v1
```

Swagger should expose these endpoints at `/docs`.

### Auth

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/auth/me
GET  /api/v1/auth/interests
PATCH /api/v1/auth/onboarding
```

### Chat

```text
POST   /api/v1/chat/sessions
GET    /api/v1/chat/sessions
GET    /api/v1/chat/sessions/{session_id}
POST   /api/v1/chat/sessions/{session_id}/messages
POST   /api/v1/chat/ask
POST   /api/v1/chat/messages/{message_id}/feedback
DELETE /api/v1/chat/sessions/{session_id}
```

### RAG

```text
GET  /api/v1/rag/search
POST /api/v1/rag/retrieve
POST /api/v1/rag/search
POST /api/v1/rag/answer
POST /api/v1/rag/semantic-retrieve
POST /api/v1/rag/retrieve-debug
```

### Admin Ingestion

```text
POST   /api/v1/admin/ingestion/start
POST   /api/v1/admin/ingestion/rebuild-from-cache
POST   /api/v1/admin/ingestion/solution-book
POST   /api/v1/admin/ingest/solution-book
GET    /api/v1/admin/ingestion/solution-book/report
GET    /api/v1/admin/ingest/solution-book/report
GET    /api/v1/admin/ingestion/sources
POST   /api/v1/admin/ingestion/sources
GET    /api/v1/admin/ingestion/sources/{source_id}
GET    /api/v1/admin/ingestion/status/{task_id}
GET    /api/v1/admin/ingestion/stats
DELETE /api/v1/admin/ingestion/clear
DELETE /api/v1/admin/ingestion/source/{source_id}
DELETE /api/v1/admin/ingestion/sources/{source_id}
GET    /api/v1/admin/ingestion/pages/{source_id}
POST   /api/v1/admin/ingestion/retry-page/{page_id}
POST   /api/v1/admin/ingestion/test-query
POST   /api/v1/admin/ingestion/test-chunk/{chunk_id}
GET    /api/v1/admin/ingestion/questions/unreviewed
POST   /api/v1/admin/ingestion/questions/{question_id}/review
```

### Curriculum And Learning

```text
GET   /api/v1/chapters
GET   /api/v1/chapters/{id}
POST  /api/v1/chapters
PATCH /api/v1/chapters/{id}

GET   /api/v1/lessons
GET   /api/v1/lessons/{id}
POST  /api/v1/lessons
PATCH /api/v1/lessons/{id}

GET    /api/v1/topics
GET    /api/v1/topics/{id}
POST   /api/v1/topics
PUT    /api/v1/topics/{id}
DELETE /api/v1/topics/{id}

GET /api/v1/elements
GET /api/v1/elements/{atomic_number}
```

### Study, Progress, Quiz, Homework, Flashcards

```text
GET    /api/v1/study-plans
GET    /api/v1/study-plans/{id}
POST   /api/v1/study-plans
PUT    /api/v1/study-plans/{id}
DELETE /api/v1/study-plans/{id}

PUT /api/v1/progress/lessons/{lesson_id}
GET /api/v1/progress/topics
GET /api/v1/progress/achievements

POST /api/v1/quizzes/generate
POST /api/v1/quizzes/submit
GET  /api/v1/quizzes/history
GET  /api/v1/quizzes/recommendations
GET  /api/v1/exams/practice

POST /api/v1/homework/solve-text
POST /api/v1/homework/solve-image
GET  /api/v1/homework/history
GET  /api/v1/homework/{homework_id}

GET  /api/v1/flashcards
POST /api/v1/flashcards
POST /api/v1/flashcards/{flashcard_id}/review
```

### Notifications

```text
GET    /api/v1/notifications
GET    /api/v1/notifications/unread-count
PATCH  /api/v1/notifications/{id}/read
PATCH  /api/v1/notifications/mark-all-read
DELETE /api/v1/notifications/{id}
GET    /api/v1/notification-preferences
PATCH  /api/v1/notification-preferences
POST   /api/v1/reminders/rebuild
```

### Health

```text
GET /health
GET /api/v1/health
```

## 6. Pydantic Schemas

Schemas are present for most APIs:

- `schemas/auth.py`
- `schemas/chat.py`
- `schemas/rag.py`
- `schemas/ingestion.py`
- `schemas/notification.py`
- `schemas/homework.py`
- `schemas/quiz.py`
- `schemas/flashcards.py`
- `schemas/progress.py`
- `schemas/preferences.py`
- `schemas/common.py`

Good points:

- Chat request supports both old and new preference fields.
- Chat response includes `answer`, `answer_text`, sources, citations, media blocks, diagnostics, confidence, route, and learning preferences.
- RAG schemas include retrieval, semantic retrieval, debug retrieval, search, and answer.
- Notification schemas cover response, unread count, and preferences.

Gaps:

- Some endpoints still return ORM objects directly through `from_attributes`, which is acceptable but should be consistently reviewed.
- Some schemas use broad `dict[str, Any]`, which is practical for diagnostics/media but should be documented for mobile consumers.
- Homework image solving schema uses `image_path`; a real app should accept file uploads or object-storage URLs.

## 7. Service Layer

Important services:

- `gemini_client.py`: central Google GenAI client wrapper.
- `ai_service.py`: tutor response generation and Gemini fallback behavior.
- `chat_service.py`: chat orchestration, RAG answer generation, dictionary/rule logic, local fallback, media routing, and session handling.
- `rag.py`: hybrid retrieval, normalization, lexical/vector scoring, caching, debug diagnostics.
- `semantic_rag.py`: advanced semantic retrieval with query rewriting, HyDE, multi-query search, fusion, reranking, and quality gates.
- `embeddings.py`: Gemini/local/hash embeddings.
- `ingestion_pipeline.py`: PDF ingestion, OCR routing, chunk creation, DB writes.
- `solution_book_ingestion.py`: solution-book extraction, units, chunks, embeddings, report generation.
- `rag_rebuild.py`: rebuild chunks from cache.
- `chunking.py`: educational chunking helpers.
- `homework_service.py`: text/image homework solving.
- `notification_service.py`: notification API behavior.
- `reminder_service.py`: rebuild reminder events.
- `learning_mode_router.py`: output mode routing.
- `tutor_prompt_builder.py`: teaching preference prompt instructions.

Main service-layer concern:

`chat_service.py` is doing too much. It should eventually be split into:

- intent/router service
- dictionary/direct-answer service
- RAG context service
- prompt builder
- generation service
- citation/media block service
- chat persistence service

There is also a minor duplication in parent-message context handling: `previous_answer = parent.content if parent.role == "assistant" else None` appears twice in the same helper.

## 8. AI And RAG Pipeline

### Current AI SDK

The backend uses the modern `google-genai` SDK through `app/services/gemini_client.py`.

No legacy `google-generativeai` production path was found in the inspected backend.

### Gemini Configuration

Settings include:

- `GEMINI_API_KEY`
- `MODEL_NAME`
- `GEMINI_DOCUMENT_MODEL`
- `GEMINI_DOCUMENT_FALLBACK_MODEL`
- `GEMINI_EMBEDDING_MODEL`
- `GEMINI_RERANKER_MODEL`
- `GEMINI_SEMANTIC_HELPERS_ENABLED`

Mismatch with expected architecture:

- Expected embedding model: `text-embedding-004`.
- Current code/.env example: `gemini-embedding-001`.
- Expected document model from previous plan: `gemini-3.5-flash`.
- `config.py` default still falls back to `gemini-2.5-flash`, while `.env.example` says `gemini-3.5-flash`.

This should be normalized before production deployment.

### Embeddings

`RagChunk.embedding` uses vector dimension 768 in PostgreSQL.

Embedding flow:

1. Try configured Gemini embedding provider.
2. If unavailable, try local multilingual embedding model.
3. If unavailable, use deterministic hash embedding fallback.

Risk:

- `sentence-transformers` is commented out in requirements, so local multilingual fallback may not be available after a clean install.
- Hash embeddings are deterministic and useful for tests, but not strong enough for production retrieval quality.

### Raw RAG

`app/services/rag.py` supports:

- Arabic normalization.
- Formula normalization.
- term expansion.
- lexical score.
- vector score.
- hybrid score.
- content/source filters.
- page/chapter/lesson/topic filters.
- Redis/in-memory caching.
- debug diagnostics.

Default `min_similarity` is now 0.45 for normal retrieval and 0.0 for debug retrieval.

### Semantic RAG

`app/services/semantic_rag.py` adds:

- Query rewriting.
- HyDE.
- Multi-query retrieval.
- RRF fusion.
- content-type intent boosts.
- optional Gemini reranking.
- quality gate logic.
- source modes:
  - `textbook_first`
  - `solution_first`
  - `balanced`
  - `solution_only`
  - `textbook_only`

This is the correct API path for mobile/chat to use when answer quality matters.

### Answer Generation

`chat_service.ask_question` handles:

- safety rules
- direct dictionary answers
- litmus/chemistry rules
- exercise solving
- RAG retrieval
- source/citation construction
- confidence
- teaching preferences
- media block requests
- local fallback when Gemini is unavailable

Important behavior:

- If Gemini is unavailable or rate-limited, the service can produce local fallback answers.
- The fallback is useful for uptime but can feel less natural than generated answers.
- The answer logic should continue moving toward semantic RAG plus direct-answer gates instead of forcing weak chunks into answers.

## 9. OCR And Document Ingestion

### Provider Interface

`app/services/ocr/base.py` defines the extraction result and provider contract.

The current production provider is Gemini:

```text
app/services/ocr/gemini_provider.py
```

It supports:

- direct PDF/document processing via Gemini Files API
- uploaded file waiting
- structured JSON response
- schema validation
- fallback models
- rendered image fallback

No OCRArena production adapter was found. That matches the expected architecture.

Missing optional providers:

- Mistral OCR provider
- PaddleOCR local fallback

These are not blockers if Gemini is the production provider, but they should be documented as future alternatives.

### Ingestion Pipeline

`app/services/ingestion_pipeline.py` handles:

- PDF page classification.
- digital text extraction.
- Gemini direct PDF extraction.
- rendered image fallback.
- quality checks.
- dry-run vs production behavior.
- page cache JSON files.
- chunking.
- extracted question persistence.
- source/chunk DB writes.

Dry-run mode:

- can classify and extract selectable text
- can warn or skip vision-required pages if Gemini is missing
- should not mark source as fully complete when required vision pages are skipped

Production mode:

- requires full handling of vision/mixed pages
- should not silently ingest incomplete scanned content

### Solution Book Ingestion

`app/services/solution_book_ingestion.py` exists and is exposed through:

```text
POST /api/v1/admin/ingestion/solution-book
POST /api/v1/admin/ingest/solution-book
```

This service is intended to make solution books first-class RAG sources beside textbooks.

Expected source types:

- `textbook`
- `solution_book`

The RAG layer supports source filtering, so textbook-only, solution-book-only, and balanced retrieval are feasible.

## 10. Multimedia Integration Points

### Text

Text answers are the only fully mature answer format.

### Image

Current support:

- page image URLs can be returned when source page images exist.
- `source_page_image_url` style blocks are supported in response models.
- `/media/books` serves textbook media.

Missing:

- real generated image service
- persistent image-generation job model
- image moderation/safety layer
- mobile upload-to-storage flow for image homework

### Audio / Voice

Current support:

- schemas and media blocks can represent audio.
- `ChatMessage.media_url` exists.
- `Reel.audio_url` exists.

Missing:

- TTS provider integration
- Celery task for TTS generation
- storage path and signed/media URL strategy
- audio readiness status API

### Video / Reels

Current support:

- `Reel` model exists.
- response schemas can represent video/reel media blocks.
- frontend can show video/reel placeholder UI.

Missing:

- video/reel retrieval service
- teacher-approved media library API
- YouTube/external video search/curation layer
- reel generation task
- media trust labeling policy in backend

### Interactive Tools

Current support:

- equation/lab routes and frontend areas exist.
- media blocks can represent CTA-style modes like quiz/flashcards/interactive.

Missing:

- first-class interactive tutoring flows
- step-by-step state machine for problem solving
- misconception detection tied to user progress

## 11. Celery, Redis, And Background Tasks

### Redis

Redis is configured through:

```text
app/core/redis.py
```

It is used for:

- Celery broker/result backend.
- semantic RAG cache helpers.

### Celery

Celery app:

```text
app/workers/celery_app.py
```

Registered task modules:

- `app.workers.ingestion_tasks`
- `app.workers.notification_tasks`

The Celery config defines a Beat schedule:

```text
check-pending-reminders-every-minute
```

But Docker/entrypoint currently starts only:

```bash
celery -A app.workers.celery_app:celery_app worker ...
```

There is no `celery beat` process in `docker-compose.yml` or the entrypoint. That means reminder scanning will not run automatically in Docker unless another process starts Beat.

### Ingestion Tasks

`ingestion_tasks.py` contains a Celery task for full PDF ingestion.

But the admin ingestion API currently uses FastAPI `BackgroundTasks` and process-local `_TASKS` for `/admin/ingestion/start`.

Risk:

- API-started ingestion state is not durable across restart.
- In-memory task progress does not scale across workers.
- Production should move API ingestion starts to Celery task ids and persist status in `IngestionJob`.

### Notification Tasks

`notification_tasks.py` scans pending `ReminderEvent` rows and creates `Notification` records if user preferences allow it.

Good points:

- respects in-app, exam, and lesson preferences.
- avoids duplicate notifications.
- updates event status to sent/skipped/failed.

Operational gap:

- needs Celery Beat or another scheduler process to execute periodically.

## 12. Chat History, RAG History, And Gemini Memory

### Are We Storing Chat History?

Yes, but only through session-based chat.

Stored tables:

- `chat_sessions`
- `chat_messages`

Session endpoint:

```text
POST /api/v1/chat/sessions/{session_id}/messages
```

This endpoint stores the user message and assistant answer as `ChatMessage` rows.

### Does `/chat/ask` Store History?

No, not by default.

`POST /api/v1/chat/ask` is a one-shot tutoring endpoint. It can accept:

- `conversation_id`
- `parent_message_id`
- `previous_question`
- `previous_answer`
- `previous_sources`
- `previous_selected_chunks`

But it does not automatically create a new `ChatSession` or store the new question/answer.

Recommendation:

- Use session endpoints for mobile conversations that need persistent history.
- Or change `/chat/ask` to optionally persist when `conversation_id` is present.

### Does Gemini Have Memory?

No persistent Gemini memory is used here.

Gemini only knows what the backend sends in each request:

- current question
- retrieved RAG context
- session history if provided by the backend
- previous answer/source fields if provided

There is no external Gemini memory/thread/session store in this codebase.

Therefore, memory is application-owned and database-backed, not Gemini-owned.

### Are We Browsing Chat History Per User?

Partly.

For session chat:

- yes.
- session ownership is checked through `get_owned_session`.
- messages are loaded for that session and used as history in generation.

For `/chat/ask`:

- only a specific `parent_message_id` can be loaded.
- the code checks the parent message belongs to a session owned by the current user.
- it does not browse all prior user messages automatically.

Recommendation:

- Add a clear `conversation_id` model or use `ChatSession.id`.
- Make `/chat/ask` optionally persist and retrieve last N messages for that conversation.
- Keep strict user ownership checks.

## 13. Chapter, Lesson, And Topic In Chemistry Book Terms

For this project, these should mean:

### Chapter

A chapter is a large ordered unit from the official Grade 9 chemistry book.

Examples:

- aqueous solutions
- acids and bases
- salts
- organic chemistry
- hydrocarbons

A chapter is useful for:

- textbook navigation
- lesson grouping
- study-plan blocks
- progress summaries
- source metadata

### Lesson

A lesson is a teachable unit inside a chapter.

Examples:

- definition of acids
- strong and weak acids
- concentration calculations
- alkane properties
- salts preparation

A lesson should map to:

- a chapter
- one or more pages
- duration estimate
- difficulty
- progress state
- related RAG chunks
- quizzes/flashcards

### Topic

A topic is a conceptual tag, not necessarily a book section.

Examples:

- H+
- molar concentration
- litmus paper
- neutralization
- HCl
- hydrocarbons
- methane

Topics are useful for:

- weak-topic detection
- adaptive quizzes
- cross-chapter review
- flashcards
- homework classification
- RAG reranking

Rule of thumb:

- Chapter = book structure.
- Lesson = teaching sequence.
- Topic = semantic concept.

## 14. Swagger And Gemini Readiness

Swagger:

- FastAPI app is correctly configured.
- Routers are included under `/api/v1`.
- OpenAPI tags are defined.
- The backend should expose APIs through `/docs`.

Gemini:

- `google-genai` is used.
- Document/PDF extraction uses Gemini direct document processing.
- Gemini generation and embeddings are wrapped behind services.
- Auth/quota failures have fallback/cooldown behavior.

Readiness gaps:

- Model names should be normalized in config and `.env.example`.
- Decide whether production embedding is `gemini-embedding-001` or `text-embedding-004`; the current repo uses `gemini-embedding-001`.
- Add a startup/preflight endpoint for Gemini model/key readiness.
- Keep local deterministic fallback for tests only, not production.
- Make Gemini quota/auth errors hidden from students but visible in diagnostics/admin logs.

## 15. Missing Features And Implementation Gaps

### Backend/API Gaps

- `/chat/ask` does not persist one-shot messages.
- Admin ingestion job progress is not fully durable.
- Per-page ingestion retry endpoint currently marks page for retry but does not execute a real page retry worker.
- Homework image solver needs a multipart upload endpoint or object-storage URL flow.
- Push notifications are not implemented despite device-token and preference fields.
- Study plan reminders need reliable scheduler deployment.
- No Celery Beat service in Docker.
- README still references OpenAI and `OPENAI_API_KEY`; docs should be updated to Gemini.

### RAG Gaps

- Embedding model config is inconsistent with target architecture.
- Local multilingual embedding dependency is commented out.
- RAG evaluation exists in tests, but should be part of CI with a clear threshold report.
- Need stronger monitoring for empty chunks, skipped pages, duplicated chunks, and weak citations.
- Need reliable source-type policy for textbook vs solution book vs exam content.

### OCR/Ingestion Gaps

- Gemini provider is production path, but no Mistral/Paddle fallback exists.
- Vision-heavy pages must be blocked in production if Gemini is missing.
- Need admin UI/API for blocked page review and selective retry.
- Need persistent ingestion artifacts index and source-file hash tracking in admin views.

### Multimedia Gaps

- TTS/audio generation not implemented.
- Generated image pipeline not implemented.
- Video/reel curation/generation not implemented.
- External media trust labels are frontend-oriented, not fully backend-enforced.
- Interactive learning flows are not first-class backend objects.

### Data Model Gaps

- `RagChunk` supports metadata but does not enforce a typed schema per source type.
- Chat/RAG retrieval history is not stored as its own analytics table.
- No explicit `RagQueryLog` or `RetrievedChunkLog` model exists for quality analytics.
- No dedicated misconception/weak-skill event model exists.

## 16. Suggested Interactive AI Feature Beyond RAG

Recommended feature: Guided Chemistry Problem-Solving Lab.

Why this is stronger than a plain RAG chatbot:

- Students do not only receive an answer.
- They solve one step at a time.
- The tutor checks each step.
- The system detects misconceptions.
- Weak topics are updated automatically.
- The final result can generate a mini quiz and flashcards.

Example flow:

1. Student enters: "محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي."
2. System identifies exercise type: concentration calculation.
3. RAG retrieves textbook formula and solution-book examples.
4. Tutor asks: "ما القانون المناسب للتركيز الغرامي؟"
5. Student answers.
6. System validates answer.
7. Tutor guides the next step.
8. Final answer includes citations and formula reasoning.
9. User progress updates weak/strong concepts.

Backend objects likely needed:

- `InteractiveSession`
- `InteractiveStep`
- `MisconceptionEvent`
- `SkillMastery`
- `TutorActionLog`

This would make EduMind feel adaptive and educational rather than only searchable.

## 17. Implementation Priorities

Recommended order:

1. Fix operational config:
   - add Celery Beat service
   - normalize Gemini model names
   - update README and `.env.example`

2. Make chat history consistent:
   - decide whether `/chat/ask` should persist
   - add conversation-aware history retrieval
   - keep user ownership checks

3. Harden RAG:
   - choose one production embedding provider
   - re-embed all sources
   - run RAG QA thresholds in CI
   - add `RagQueryLog` for analytics

4. Harden ingestion:
   - move admin ingestion start to Celery
   - persist status only in DB
   - implement real per-page retry
   - add blocked-page review flow

5. Complete notifications:
   - start Celery Beat in Docker
   - test reminder rebuild and delivery end-to-end
   - add push provider later if needed

6. Add multimedia gradually:
   - TTS first
   - image/page media second
   - video/reel library third
   - interactive solver as the main differentiated feature

## 18. Verification Notes

Inspected and verified:

- backend folders and key files exist
- API router inclusion
- chat/RAG route shape
- notification route shape
- ingestion route shape
- schemas for chat/RAG/notifications
- Celery and notification tasks
- Redis helper
- Docker entrypoint behavior
- Python compile check for key route/import modules

Compile check passed for:

```text
app/api/ingestion/routes.py
app/api/router.py
app/main.py
```

Important note for local running:

- Backend app routes are under `/api/v1`.
- Swagger is `/docs`.
- Health is available at both `/health` and `/api/v1/health`.
- Production-like DB requires PostgreSQL with pgvector.
- SQLite local mode exists but should not be treated as production vector retrieval quality.
