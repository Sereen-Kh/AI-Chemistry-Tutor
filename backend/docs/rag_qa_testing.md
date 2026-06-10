# EduMind RAG QA Testing

This document explains the deterministic QA suite for the Grade 9 Chemistry RAG APIs.

## What It Tests

The suite covers:

- `POST /api/v1/rag/retrieve`
- `POST /api/v1/chat/ask`
- `POST /api/v1/homework/solve-text`

The QA dataset lives at:

```text
backend/tests/fixtures/rag_grade9_qa_cases.json
```

Each case contains:

- `id`
- `category`
- `question`
- `expected_answer_keywords`
- `forbidden_keywords`
- `expected_source_topics`
- `min_confidence`
- `expected_behavior`
- `endpoint_targets`

## Unit Mode

Unit mode is deterministic and is the default. It does not call Gemini, PostgreSQL, Redis, pgvector, or Celery.

The tests override auth/database dependencies and monkeypatch the RAG/chat/homework services with stable fixture-backed responses.

Run:

```bash
cd backend
.venv/bin/python -m pytest tests/test_rag_grade9_qa.py
```

Generate a JSON report:

```bash
cd backend
.venv/bin/python -m scripts.run_rag_qa_suite
```

The report is written to:

```text
backend/reports/rag_qa_report.json
```

## Integration Mode

Integration mode calls the real FastAPI routes and real backend services. It may require a configured database, indexed RAG chunks, Redis, and local embedding settings.

Run only when the local backend data stack is ready:

```bash
cd backend
RUN_RAG_INTEGRATION=1 EMBEDDING_PROVIDER=local_hash .venv/bin/python -m pytest tests/test_rag_grade9_qa.py
```

Or export a report:

```bash
cd backend
RUN_RAG_INTEGRATION=1 EMBEDDING_PROVIDER=local_hash .venv/bin/python -m scripts.run_rag_qa_suite --mode integration
```

## Live Gemini Mode

The default QA suite must not use live Gemini calls.

To test live Gemini behavior, first enable integration mode and provide valid model credentials:

```bash
cd backend
RUN_RAG_INTEGRATION=1 GEMINI_API_KEY=... EMBEDDING_PROVIDER=gemini .venv/bin/python -m pytest tests/test_rag_grade9_qa.py
```

Use this only for explicit integration runs because it can consume quota and may fail due to rate limits.

## Failure Output

Failures include:

- case id
- category
- question text
- expected keywords
- forbidden keywords
- actual answer
- retrieved chunk previews
- full response payload

The report groups failures by stage:

- `retrieval`
- `generation`
- `citation`
- `confidence`
- `hallucination_guard`
- `http`
- `endpoint`

## Adding Cases

Add new objects to `backend/tests/fixtures/rag_grade9_qa_cases.json`.

For answerable textbook cases:

- set `expected_behavior` to `answerable`
- include at least two `expected_answer_keywords`
- include source topics that should appear in retrieved chunks
- set a realistic `min_confidence`, usually `0.68` to `0.80`
- include all endpoint targets unless the case is endpoint-specific

For out-of-scope cases:

- set `expected_behavior` to `out_of_scope`
- use `expected_answer_keywords` like `["لم أجد", "غير كاف"]`
- keep `expected_source_topics` empty
- set `min_confidence` to `0.0`
- add forbidden keywords that would indicate hallucinated citations or fabricated confident answers

Keep the fixture deterministic. Do not add fields that require live model calls unless they are guarded by integration mode.
