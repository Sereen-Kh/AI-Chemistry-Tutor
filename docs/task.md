# Semantic RAG Execution Checklist

Source plan: `docs/implementation_plan_new.md`

## Current Decisions

- Vector store: PostgreSQL with pgvector, using the existing `rag_chunks` table.
- Solutions ingestion path: synchronous CLI via `backend/scripts/ingest_pdf.py`.
- Solutions source type: `solutions`.
- Reranker model: `gemini-2.0-flash`.
- Celery remains the future path for admin/web uploads, not the immediate execution path.

## Checklist

- [x] Confirm PostgreSQL/pgvector and Redis are running.
- [x] Ingest `data/textbooks/syria_grade_9/Solutions_Chemistry.pdf` as `source_type=solutions`.
- [x] Verify `content_sources` has the Solutions source.
- [x] Verify `rag_chunks` has 82 distinct pages for the Solutions source.
- [x] Verify `rag_chunks.embedding` is a pgvector `vector(768)` column.
- [x] Verify direct RAG retrieval returns Solutions chunks for solution-style questions.
- [x] Rebuild cached textbook pages into PostgreSQL/pgvector for dual-source retrieval.
- [x] Add source routing service for `textbook`, `solutions`, and `both`.
- [x] Add semantic RAG service with query rewrite, HyDE, multi-query, pgvector search, RRF, and Gemini rerank.
- [x] Integrate semantic retrieval into `chat_service.py`.
- [x] Add `backend/scripts/test_semantic_rag.py`.
- [x] Run verification queries for textbook, solutions, and mixed intents.
- [ ] Document remaining quality gaps and follow-up work.

## Execution Notes

- Ingestion can use selectable text only when OCR is explicitly not required for vision pages.
- Production OCR should not be considered complete for scanned/mixed pages unless Gemini extraction is configured and required.
- Local smoke tests may use `EMBEDDING_PROVIDER=local_hash`; production should use one stable embedding provider and re-embed all chunks after changing it.
- 2026-06-07: Ingested Solutions source into PostgreSQL/pgvector with `source_id=2`, `875` chunks, `82` distinct pages, and top retrieval page `51` for the page 117 acid table query.
- 2026-06-07: Rebuilt textbook cache into PostgreSQL/pgvector with `source_id=3`, `672` chunks, `96` stored pages, and `134` extracted questions.
- 2026-06-07: Semantic RAG smoke test passed for `ما هي الحموض؟`, Solutions page 117 acid table, and mixed explain+solve prompts.
- 2026-06-07: Known content gap: `ما هو الجدول الدوري؟` routes correctly to `textbook` but returns no chunks from the current cached textbook source.
