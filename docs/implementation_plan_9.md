# Upgrade to Semantic RAG with Dual-Source Support (Textbook + Solutions Book)

Upgrade the tutor's RAG retrieval pipeline to understand student questions semantically using query expansion, Hypothetical Document Embeddings (HyDE), multi-query generation, Reciprocal Rank Fusion (RRF), and Gemini cross-encoder reranking. We will also ingest the Grade 9 Chemistry Solutions Book and support smart source routing (textbook vs. solutions vs. both) over the existing PostgreSQL/pgvector database.

## User Review Required

> [!IMPORTANT]
> **Database Architecture (PostgreSQL/pgvector vs. Qdrant):**
> While `edumind_semantic_rag_architecture.md` mentions using Qdrant, the codebase's official API contract document (`docs/ai_api_contracts.html`) explicitly states:
> *   **"Production vector store: PostgreSQL with pgvector, VECTOR(768)."**
> *   **"Production must not use Qdrant."**
> 
> To align with the existing production system, we propose implementing all 6 semantic stages (Query Rewriting, HyDE, Multi-Query, Search, RRF, and Gemini Reranking) but querying the existing PostgreSQL `rag_chunks` database table (using pgvector) instead of deploying a new Qdrant database. This prevents configuration drift and keeps the stack lightweight and robust.

> [!TIP]
> **Ingestion Script reuse:**
> The solutions book `Solutions_Chemistry.pdf` exists under `data/textbooks/syria_grade_9/Solutions_Chemistry.pdf`. Rather than writing a standalone custom parser from scratch, we propose using the robust, existing OCR/Gemini-based ingestion script `backend/scripts/ingest_pdf.py` with `--source-type solutions` to extract, chunk, embed, and store the pages into the PostgreSQL database.

## Open Questions

> [!NOTE]
> 1. **Celery vs. Direct Ingestion:** Would you like the solutions book ingestion to run as a background task through Celery (which is the target for large books in production), or should we run it synchronously using `backend/scripts/ingest_pdf.py`?
> 2. **Reranker Model Options:** We plan to use `gemini-2.0-flash` for the cross-encoder reranking step (Stage 6) since it is fast and has native multilingual/Arabic capabilities. Let us know if you prefer to use a local cross-encoder model.

## Proposed Changes

---

### 1. Ingestion of Chemistry Solutions Book

We will ingest `data/textbooks/syria_grade_9/Solutions_Chemistry.pdf` into the PostgreSQL database using the existing ingestion pipeline, designating its `source_type` as `"solutions"`.

#### [MODIFY] [ingestion_pipeline.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ingestion_pipeline.py)
*   Ensure that the chunk metadata and payload attributes correctly reflect `source_type = "solutions"` or `"textbook"`.
*   Verify the page extraction formats successfully chunk formulas and worked chemistry examples.

---

### 2. Semantic RAG Services

We will implement the upgraded retrieval architecture.

#### [NEW] [semantic_rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/semantic_rag.py)
Create a new service module containing the 6-stage pipeline:
*   **Stage 1: Query Rewriting:** Use `gemini-2.0-flash` to clarify and expand the student's Arabic chemistry question with appropriate terminology.
*   **Stage 2: HyDE:** Generate a hypothetical textbook-style answer and embed it using the Google `text-embedding-004` model.
*   **Stage 3: Multi-Query:** Generate 3 alternative formulations of the user's question.
*   **Stage 4: pgvector Vector Search:** Run asynchronous vector queries in parallel (using `asyncio.gather`) against pgvector on the `rag_chunks` table, supporting filters for `"textbook"`, `"solutions"`, or `"both"`.
*   **Stage 5: Reciprocal Rank Fusion (RRF):** Combine the search results from the rewritten query, multi-query variations, and HyDE vector.
*   **Stage 6: Cross-Encoder Reranking:** Run parallel Gemini calls to score candidate chunks (relevance 0-10) and return the top 5 chunks.
*   **Caching:** Store query rewrites (TTL=600s) and fused/reranked RAG contexts (TTL=3600s) in Redis.

#### [NEW] [source_router.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/source_router.py)
*   Create an intent classifier that inspects Arabic query keywords.
*   Route keywords like `احسب، حل، أوجد، وازن` to `"solutions"`.
*   Route keywords like `عرّف، ما هو، اشرح، فسر` to `"textbook"`.
*   Default to `"both"` otherwise.
*   Cache the routing results in Redis.

---

### 3. API Integration

We will connect the new semantic RAG pipeline to the tutor's chat loop.

#### [MODIFY] [chat_service.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chat_service.py)
*   Update `send_message` and `ask_question` to route the student's query using `source_router.py`.
*   Call `semantic_rag.py` to retrieve the top 5 grounded chunks.
*   Format system prompts using references to both textbook sources (e.g. `[من الكتاب المدرسي — صفحة X]` or `[من كتاب الحلول — صفحة Y]`).

---

### 4. Verification & Testing

#### [NEW] [test_semantic_rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/scripts/test_semantic_rag.py)
*   Create a test script containing chemistry queries mapping to Textbook, Solutions, and Mixed intents.
*   Measure and output:
    1. The routed target source.
    2. The rewritten query.
    3. Retrieval scores, source labels, page numbers, and snippet previews.
    4. Overall execution latency (ms).

## Verification Plan

### Automated Tests
Run the newly created semantic search verification script:
```bash
python3 backend/scripts/test_semantic_rag.py
```
Verify that the output contains correct source classification, RRF fusion results, and low latency.

### Manual Verification
*   Ask the tutor: `"ما هو الجدول الدوري؟"` -> verify context is retrieved from the textbook source.
*   Ask the tutor: `"احسب الكتلة المولية لـ H2SO4"` -> verify context is retrieved from the solutions source.
*   Ensure that the final answers cite the correct page numbers and book sources.
