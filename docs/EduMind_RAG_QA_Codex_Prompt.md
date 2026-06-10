# Codex / Claude Prompt - EduMind RAG QA Testing

You are a senior QA automation engineer and backend test architect working on the EduMind FastAPI backend.

Goal:
Build a practical QA test suite for the EduMind Grade 9 Chemistry RAG system. The system should answer questions from the indexed chemistry textbook, retrieve the correct source chunks, avoid hallucinations, handle Arabic normalization, and expose useful diagnostics for debugging.

Important project context:
- Backend: FastAPI, SQLAlchemy, PostgreSQL/pgvector, Redis, Celery.
- RAG endpoints include:
  - POST /api/v1/chat/ask
  - POST /api/v1/rag/retrieve
  - POST /api/v1/rag/retrieve-debug if present
  - POST /api/v1/homework/solve-text
- RAG implementation uses Gemini embeddings, local fallback embeddings, Arabic normalization, lexical scoring, vector scoring, hybrid scoring, and source page metadata.
- The Grade 9 chemistry content includes aqueous solutions, concentration, acids, bases, reaction types, salts, organic chemistry, hydrocarbons, and alkanes.

Tasks:
1. Create `backend/tests/fixtures/rag_grade9_qa_cases.json` with at least 50 cases. Each case must include: id, category, question, expected_answer_keywords, forbidden_keywords, expected_source_topics, min_confidence, expected_behavior, endpoint_targets.
2. Create `backend/tests/test_rag_grade9_qa.py` with pytest parameterized tests for `/rag/retrieve`, `/chat/ask`, and `/homework/solve-text`.
3. Do not call real Gemini APIs by default. Mock Gemini generation and embeddings, or use deterministic/local embedding fallback. Only run live integration tests when `RUN_RAG_INTEGRATION=1` is set.
4. Add Arabic normalization tests for: `الحموض القوية`, `الحُمُوضُ القَوِيَّة`, `احماض قويه`, `H₂O`, `H2O`, `التركيز المولي`, `التركز المولي`.
5. Add citation/source grounding tests requiring chunk_id/source_id/page_number/similarity_score or equivalent metadata for answerable cases.
6. Add hallucination guard tests for out-of-scope questions. The system must not fabricate textbook citations or confident answers.
7. Create `backend/scripts/run_rag_qa_suite.py` to run the dataset and export `backend/reports/rag_qa_report.json`.
8. Create `backend/docs/rag_qa_testing.md` explaining unit mode, integration mode, live Gemini mode, and how to add cases.

Acceptance criteria:
- Existing tests still pass.
- The default test run requires no Gemini API key.
- Failures clearly identify whether retrieval, generation, citation, or hallucination guard failed.
- Failure messages show question id, question text, expected keywords, actual answer, and retrieved chunk previews.
- Do not rewrite production code unless needed to expose testable diagnostics.

Implementation rules:
- Inspect the codebase first. Do not guess paths.
- Use the existing FastAPI test client / async client pattern already used in the project.
- Reuse existing factories/fixtures where present.
- If an endpoint does not exist, document it and skip that part with `pytest.skip`, not hard failure.
- Keep tests deterministic.
