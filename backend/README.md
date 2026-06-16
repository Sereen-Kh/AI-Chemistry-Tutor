# EduMind Backend

FastAPI backend for the EduMind Grade 9 Chemistry Tutor.

The backend uses:

- FastAPI
- PostgreSQL with pgvector for production RAG
- SQLite fallback for local development
- Redis and Celery for background work
- Google GenAI / Gemini for tutoring, document extraction, and embeddings

## Setup

```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in at least:

```env
GEMINI_API_KEY=...
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSION=768
EMBEDDING_PROVIDER=gemini
ALLOW_HASH_EMBEDDINGS=false
ALLOW_LOCAL_EMBEDDINGS=false
RAG_QUERY_LOGGING_ENABLED=true
```

Hash embeddings are for deterministic tests only. Production ingestion and re-embedding should fail clearly if Gemini embeddings are unavailable.

## Run

```bash
uvicorn app.main:app --reload
```

Swagger is available at:

```text
http://localhost:8000/docs
```

Main API prefix:

```text
/api/v1
```

## RAG Maintenance

Re-embed all chunks through Swagger:

```text
POST /api/v1/admin/rag/reembed
GET  /api/v1/admin/rag/reembed/status/{job_id}
```

Run retrieval evaluation from the CLI:

```bash
python scripts/evaluate_rag.py --fail-on-threshold
```

Reports are written to:

```text
data/eval/reports/rag_eval_latest.json
data/eval/reports/rag_eval_latest.md
```
