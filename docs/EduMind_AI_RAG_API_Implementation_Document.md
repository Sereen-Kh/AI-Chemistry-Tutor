# EduMind API Implementation Document - AI and RAG System

**Date:** 2026-06-03  
**Scope:** This document lists the external AI APIs first, then the EduMind backend APIs currently implemented for the RAG system, then the APIs still recommended for implementation.

> Note: I use **RAG** here for retrieval-augmented generation. If “rack system” meant another module name, rename this section only; the API logic remains the same.

---

## 1. Executive API Map

```text
Student/Admin UI
   |
   |-- Auth/Profile/Curriculum APIs
   |-- Chat + Homework + Quiz APIs
   |-- RAG retrieval APIs
   |-- Admin ingestion/review APIs
         |
         |-- PDF/Text extraction -> Chunking -> Embedding -> pgvector
         |-- Gemini generation / Gemini OCR / Gemini embedding
```

## 2. External AI APIs - First Priority

| # | External API | Model/API | Used For | Status | Implementation Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Gemini generateContent | gemini-3.5-flash | Tutor chat, homework solving, quiz/flashcard/study-plan generation | Implemented | Wrapped by ai_service.py; free-text generation with RAG context and fallback to local RAG. |
| 2 | Gemini generateContent JSON mode | gemini-3.5-flash | Structured OCR / page understanding | Implemented | Uses response_schema=PageExtractionResult, temperature=0.0, max tokens 8192. |
| 3 | Gemini generateContent fallback | gemini-2.5-pro | OCR fallback when primary extraction fails quality checks | Implemented | Triggered after PDF extraction and rendered-image primary model fail quality gate. |
| 4 | Gemini embedContent | text-embedding-004 | RAG embeddings for documents and user queries | Implemented | 768-dim vectors; RETRIEVAL_DOCUMENT for chunks and RETRIEVAL_QUERY for user questions. |
| 5 | Gemini files.upload | PDF Files API | Upload PDF once and reference it during per-page extraction | Implemented | Used by document provider before structured page extraction. |
| 6 | Deterministic fallback embedding | Local hash vector | Local/dev fallback if GEMINI_API_KEY is unavailable | Implemented | Not an external API; preserves pipeline execution locally. |
| 7 | Local RAG answer fallback | Rule/lexical extraction | Answer from retrieved textbook chunks when Gemini fails/quota is exhausted | Implemented | Not an external API; protects chat/ask from hard failure. |

## 3. Implemented EduMind AI/RAG Endpoints

| Method | Path | Auth | Purpose | Status | RAG/AI Role |
| --- | --- | --- | --- | --- | --- |
| POST | /api/v1/chat/sessions/{session_id}/messages | Bearer | Multi-turn AI chat | Implemented | Saves user message, retrieves RAG context, calls Gemini, saves assistant answer. |
| POST | /api/v1/chat/ask | Bearer | Stateless RAG answer | Implemented | Direct answer router -> hybrid retrieval -> confidence gate -> Gemini/local fallback. |
| POST | /api/v1/homework/solve-text | Bearer | Solve typed homework problem | Implemented | Uses RAG context and AI answer generation. |
| POST | /api/v1/homework/solve-image | Bearer | OCR image then solve | Implemented | Image -> GeminiDocumentProvider.extract_page() -> text -> solve_text(). |
| POST | /api/v1/rag/retrieve | Bearer | Direct vector/hybrid retrieval | Implemented | JSON body; returns RetrievedChunk list. |
| GET | /api/v1/rag/search | Bearer | Direct vector/hybrid retrieval | Implemented | Query parameters; returns RetrievedChunkResponse[]. |
| POST | /api/v1/quizzes/generate | Public | Generate quiz from extracted questions/context | Implemented | Uses extracted questions and AI generation path depending on service. |
| GET | /api/v1/quizzes/recommendations | Public | AI-recommended quizzes | Implemented | Recommendation endpoint documented in API map. |
| POST | /api/v1/study-plans | Bearer | Create study plan | Implemented | Stores plan_json; AI study-plan service documented separately. |

## 4. Implemented Admin Ingestion / RAG Operations

| Method | Path | Purpose | Status | Notes |
| --- | --- | --- | --- | --- |
| POST | /api/v1/admin/ingestion/start | Start PDF ingestion | Implemented | Creates source/job, classifies pages, extracts text/OCR, chunks, embeds, stores RagChunk/ExtractedQuestion. |
| GET | /api/v1/admin/ingestion/status/{task_id} | Poll ingestion progress | Implemented | Reports pages/chunks/questions/diagrams/tables/equations and failures. |
| GET | /api/v1/admin/ingestion/sources | List content sources | Implemented | Source registry view. |
| POST | /api/v1/admin/ingestion/sources | Register source | Implemented | Metadata-only source registration. |
| GET | /api/v1/admin/ingestion/sources/{source_id} | Source details | Implemented | Read source metadata. |
| DELETE | /api/v1/admin/ingestion/source/{source_id} | Delete source + chunks | Implemented | Remove a source and its RAG data. |
| DELETE | /api/v1/admin/ingestion/sources/{source_id} | Delete source + chunks | Implemented | Duplicate/alternate path documented. |
| GET | /api/v1/admin/ingestion/stats | Global ingestion statistics | Implemented | Counts chunks/sources/questions, reviewed/unreviewed, avg chunk length, etc. |
| DELETE | /api/v1/admin/ingestion/clear | Clear all RAG chunks | Implemented | Dangerous admin operation; should require explicit confirmation in UI. |
| GET | /api/v1/admin/ingestion/pages/{source_id} | Per-page ingestion status | Implemented | Needed for OCR quality triage. |
| POST | /api/v1/admin/ingestion/retry-page/{page_id} | Retry failed page | Implemented | Current page-level recovery endpoint. |
| POST | /api/v1/admin/ingestion/test-query | Test RAG retrieval | Implemented | Admin diagnostics for query retrieval. |
| POST | /api/v1/admin/ingestion/test-chunk/{chunk_id} | Find similar chunks | Implemented | Admin diagnostics for embedding/retrieval quality. |
| GET | /api/v1/admin/ingestion/questions/unreviewed | Unreviewed extracted questions | Implemented | Question review queue. |
| POST | /api/v1/admin/ingestion/questions/{question_id}/review | Review/edit extracted question | Implemented | Human-in-the-loop assessment cleanup. |

## 5. Core RAG Data Models Already Present

| Model | Table | Purpose |
| --- | --- | --- |
| ContentSource | content_sources | PDF/source registry: title, type, grade, subject, year, file_path, status, metadata. |
| RagChunk | rag_chunks | Main vector store: content, normalized_content, content_type, page_number, chapter/lesson/topic links, 768-dim embedding. |
| ExtractedQuestion | extracted_questions | Questions extracted from textbook/exam pages; supports review workflow and quiz generation. |
| IngestionJob | ingestion_jobs | Tracks ingestion execution/job state. |
| IngestionPage | ingestion_pages | Per-page status, warnings, errors, extraction result tracking. |
| ChatSession / ChatMessage | chat_sessions / chat_messages | Stores multi-turn tutor chat and AI latency/feedback. |

## 6. Other Backend API Groups Already Implemented

| Group | Status | Representative Endpoints |
| --- | --- | --- |
| Identity/Profile | Implemented | /auth/register, /auth/login, /auth/me, /auth/interests, /auth/onboarding, /users/me, /student-profile/me |
| Curriculum | Implemented | /chapters, /lessons, /topics, /elements |
| Chat + RAG | Implemented | /chat/sessions, /chat/sessions/{id}/messages, /chat/ask, /rag/search, /rag/retrieve |
| Assessment | Implemented | /quizzes/generate, /quizzes/submit, /quizzes/history, /quizzes/recommendations, /exams/practice |
| Homework | Implemented | /homework/solve-text, /homework/solve-image, /homework/history, /homework/{id} |
| Flashcards | Implemented | /flashcards, /flashcards/{id}/review |
| Progress/Gamification | Implemented | /progress/lessons/{id}, /progress/topics, /progress/achievements |
| Study Plans | Implemented | /study-plans CRUD |
| Admin Ingestion | Implemented | /admin/ingestion/* |
| Health | Implemented | /health, /api/v1/health |

## 7. APIs Still Recommended for the RAG System

| Priority | Method | Path | Auth | Purpose | Why Needed |
| --- | --- | --- | --- | --- | --- |
| P0 | POST | /api/v1/admin/ingestion/upload | Admin | Upload PDF via multipart/form-data instead of server-local pdf_path | Current start endpoint assumes pdf_path. This is risky for frontend/admin UX and deployment portability. |
| P0 | POST | /api/v1/admin/ingestion/jobs/{task_id}/cancel | Admin | Cancel running ingestion job | Needed because OCR/PDF ingestion is long-running and costly. |
| P0 | POST | /api/v1/admin/ingestion/pages/{page_id}/reprocess | Admin | Reprocess one page with provider/mode/options | retry-page exists, but reprocess should accept OCR provider, force image/PDF mode, DPI, and quality thresholds. |
| P0 | GET | /api/v1/rag/debug | Admin | Return normalized query, expansions, vector score, lexical score, final score, selected chunks | Critical for diagnosing inaccurate RAG answers and Arabic normalization problems. |
| P0 | POST | /api/v1/rag/evaluate | Admin | Run golden question set and return recall/precision/source-hit/confidence metrics | Needed to verify improvements after changing chunking, embeddings, OCR, dictionary, or prompts. |
| P0 | POST | /api/v1/rag/feedback | Bearer | Capture answer correctness, selected source quality, expected answer/source | Turns user/customer feedback into retrievable evaluation data. |
| P0 | GET/POST/PATCH/DELETE | /api/v1/knowledge/terms | Admin | Chemistry dictionary/glossary CRUD: term, aliases, Arabic normalization, formula, definition, source | Needed for questions not directly answered by textbook chunks and for formula/equation routing. |
| P0 | GET | /api/v1/knowledge/terms/search | Bearer | Student/query-time dictionary lookup | Lets the RAG system and frontend expose exact formula/definition matches before calling AI. |
| P1 | POST | /api/v1/rag/answer | Bearer | Dedicated RAG answer endpoint separate from chat | chat/ask exists, but a RAG-named endpoint makes testing and mobile integration cleaner. |
| P1 | GET | /api/v1/admin/rag/chunks/{chunk_id} | Admin | Inspect a chunk with embedding metadata, source page, extracted tables/equations | Needed for quality review of bad retrieval cases. |
| P1 | PATCH | /api/v1/admin/rag/chunks/{chunk_id} | Admin | Edit/approve/reject a chunk and trigger re-embedding | Question review exists; chunk review is also needed. |
| P1 | POST | /api/v1/admin/rag/reindex | Admin | Recompute embeddings/indexes for a source or all chunks | Needed when embedding model, chunking, normalization, or dictionary changes. |
| P1 | POST | /api/v1/admin/rag/cache/clear | Admin | Clear Redis RAG cache by source/query/all | Current cache TTL exists; explicit invalidation is required after ingestion/reindex. |
| P1 | GET | /api/v1/ai/capabilities | Public/Bearer | Expose enabled models, supported formats, OCR availability, upload limits | Frontend can adapt UI instead of hardcoding model/provider assumptions. |
| P1 | POST | /api/v1/chat/ask/stream | Bearer | SSE/streaming RAG answer | Improves UX for long Gemini responses; not required for correctness. |
| P2 | GET | /api/v1/admin/ai/usage | Admin | Gemini call counts, latency, quota errors, fallback rate by service | Needed for cost/quality monitoring. |
| P2 | POST | /api/v1/admin/prompts/test | Admin | Test prompt templates with fixed RAG context | Useful during prompt tuning and regression checks. |
| P2 | GET | /api/v1/admin/ingestion/jobs | Admin | List historical ingestion jobs | Complements status/{task_id}; useful for admin dashboard. |

## 8. Recommended Implementation Order

| Step | Area | Action |
| --- | --- | --- |
| 1 | Stabilize current RAG | Add /rag/debug, /rag/evaluate, /rag/feedback; define golden Arabic chemistry questions. |
| 2 | Make ingestion production-ready | Add PDF upload, job cancel, page reprocess with OCR options, cache invalidation. |
| 3 | Add chemistry knowledge dictionary | Create KnowledgeTerm model + admin CRUD + student search + router integration. |
| 4 | Add human review of retrieval data | Chunk inspect/edit/reject/approve endpoints; re-embed changed chunks. |
| 5 | Improve UX and operations | Streaming answer, AI usage dashboard, capabilities endpoint, prompt test endpoint. |

## 9. Recommended Public API Boundary

Do **not** expose Gemini directly to frontend clients. The frontend should call EduMind backend APIs only. The backend should own API keys, model selection, prompt construction, RAG retrieval, fallback logic, and usage logging.

Recommended boundary:

```text
Frontend/mobile
   -> /chat/ask or /chat/sessions/{id}/messages
   -> /homework/solve-text or /homework/solve-image
   -> /rag/retrieve only for internal/admin diagnostics or advanced UI
   -> /knowledge/terms/search for deterministic formulas/definitions

Backend
   -> Gemini generateContent
   -> Gemini embedContent
   -> Gemini files.upload
   -> PostgreSQL pgvector
   -> Redis cache
```

## 10. Highest-Risk Missing Items

1. **No direct PDF upload endpoint**: current ingestion is path-based. This is fragile outside local/dev environments.
2. **No RAG debug endpoint**: hard to understand why an answer is wrong when hybrid scoring selects poor chunks.
3. **No evaluation API**: no automated measurement of answer/source quality after changes.
4. **No knowledge dictionary CRUD**: chemical formulas, aliases, Arabic spelling variants, and textbook synonyms should be managed separately from PDF chunks.
5. **No chunk review/edit workflow**: question review exists, but bad chunks and OCR mistakes also need review and re-embedding.
6. **No explicit cache invalidation**: Redis cache can return old retrieval results after ingestion/reindex unless manually expired.

---

## 11. Codex/Implementation Prompt Starter

```text
Create the missing RAG system APIs for EduMind backend in this order:
1. /api/v1/admin/ingestion/upload - multipart PDF upload and source creation.
2. /api/v1/rag/debug - show normalized query, expanded terms, vector score, lexical score, blended score, and selected chunks.
3. /api/v1/rag/evaluate - run golden question set and return retrieval/source/answer metrics.
4. /api/v1/rag/feedback - store user feedback on answer correctness and source usefulness.
5. /api/v1/knowledge/terms CRUD - chemistry dictionary with Arabic aliases, formulas, definitions, and source references.
6. /api/v1/admin/rag/chunks inspect/edit/reject/approve + re-embed changed chunks.
7. /api/v1/admin/rag/reindex and /api/v1/admin/rag/cache/clear.

Keep Gemini calls server-side only. Reuse existing auth, SQLAlchemy patterns, Pydantic schemas, async service wrappers, Redis cache, and pgvector retrieval style.
```
