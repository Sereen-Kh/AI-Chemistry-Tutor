# EduMind — Master Implementation Prompt for Claude Sonnet 4.5 (GitHub Copilot)

> Copy this entire prompt into GitHub Copilot Chat or Cursor Composer.
> Attach the files referenced in the context section before sending.

---

## 🧠 ROLE & CONTEXT

You are a **senior full-stack engineer and AI/ML architect** working on a production FastAPI + PostgreSQL application. You write clean, typed, production-ready Python code with full error handling. You never write pseudocode — always real, runnable implementations.

The project is **EduMind**, an AI-powered Chemistry Tutor for Grade 9 students. The backend is:

- **FastAPI** (Python 3.11+) with async/await throughout
- **SQLAlchemy 2.0** (async) with **Alembic** for migrations
- **PostgreSQL 15** with the **pgvector** extension for vector similarity search
- **Redis** for caching, rate limiting, and Celery task queues
- **Celery** for async background tasks (PDF processing, TTS, image generation)
- **LangChain** for RAG orchestration
- The app structure follows a **feature-based** layout: `app/api/`, `app/models/`, `app/services/`, `app/workers/`

---

## 📋 YOUR TASKS — DO ALL OF THESE IN ORDER

---

### TASK 1 — Build all missing SQLAlchemy models from the ERD

Open the file `docs/erd-diagram.md`. Read the full ERD carefully.

Build **every missing SQLAlchemy model** that does not yet exist in `app/models/`. Use `SQLModel` (which combines SQLAlchemy + Pydantic). Each model must have:

- Proper Python type hints on every field
- `Field(...)` with constraints: `nullable`, `unique`, `index`, `default`, `foreign_key`
- `__tablename__` explicitly set
- Relationships defined with `Relationship()` where appropriate
- A corresponding **Alembic migration file** in `migrations/versions/`

The models you MUST create (check which ones are already in `app/models/` and skip those):

```
users                  — auth only (email, hashed_password, email_verified)
student_profiles       — all learning preferences (teaching_style, answer_format, language, xp, level, streak_days, exam_date)
interest_categories    — seed table (key, name_ar, name_en, icon, display_order)
user_interests         — junction table (user_id FK, interest_id FK)  [M2M]
chapters               — curriculum chapters (title_ar, title_en, order, difficulty, icon)
lessons                — lesson content (chapter_id FK, title_ar, content_ar, order, difficulty, duration_min)
lesson_progress        — per-user lesson tracking (user_id FK, lesson_id FK, status enum, completed_at)
chat_sessions          — AI chat sessions (user_id FK, lesson_id FK nullable, title, style)
chat_messages          — chat messages (session_id FK, role enum, content, format enum, feedback enum, media_url)
topics                 — quiz/flashcard categories (title_ar, category, difficulty, order)
questions              — quiz questions (topic_id FK, question_ar, options JSONB, correct_answer int, explanation_ar, difficulty)
quiz_attempts          — quiz results (user_id FK, topic_id FK, score, total, answers JSONB, weak_topics JSONB)
flashcards             — flashcard content (topic_id FK, front_ar, back_ar, created_by enum)
flashcard_progress     — SM-2 spaced repetition (user_id FK, flashcard_id FK, mastered bool, ease_factor float, interval_days int, next_review_at date)
study_plans            — AI-generated plans (user_id FK, exam_date, plan_json JSONB, status enum)
achievements           — earned badges (user_id FK, slug, icon, earned_at)
textbook_chunks        — RAG vector store (chapter_id FK nullable, page_number int, content TEXT, source VARCHAR, embedding VECTOR(768))
subscriptions          — Stripe billing (user_id FK UNIQUE, stripe_customer_id, stripe_subscription_id, plan enum, status enum, trial_messages_used int, current_period_end)
reels                  — cached AI audio reels (lesson_id FK UNIQUE, audio_url, script TEXT, visual_cues JSONB, duration_seconds int, generated_at)
device_tokens          — FCM push notification tokens (user_id FK, token TEXT UNIQUE, platform enum)
homework               — AI-solved problems (user_id FK, topic_id FK nullable, problem_text TEXT, solution TEXT)
user_progress          — aggregated topic stats (user_id FK, topic_id FK, flashcards_mastered int, quizzes_completed int, best_quiz_score float, last_activity)
```

**IMPORTANT on textbook_chunks.embedding dimension:**

- Use `VECTOR(768)` — we will use Google's `text-embedding-004` model (768-dim output)
- Do NOT use 1536 — that is OpenAI's dimension, we are NOT using OpenAI for embeddings
- The pgvector index must be: `CREATE INDEX ON textbook_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);`

After creating all models, generate ONE Alembic revision that creates all tables:

```bash
alembic revision --autogenerate -m "add_all_missing_tables"
alembic upgrade head
```

---

### TASK 2 — Chemistry PDF ingestion pipeline with OCR + Gemini 2.5 Flash

The Chemistry textbook PDF is at `data/chemistry_book.pdf`. This PDF is a **mixed document** — it contains:

- Some pages with **selectable text** (digital text layer)
- Other pages with **non-selectable content** (scanned images, diagrams, handwritten notes, chemical equations rendered as images)

You must extract ALL content from every page — both text and image-based content.

#### 2A — PDF Analysis & Page Classification

Create `app/services/pdf_processor.py` with a function `classify_pages(pdf_path: str) -> dict` that:

1. Opens the PDF with `pdfplumber`
2. For each page, checks if it has extractable text (>50 characters after stripping whitespace)
3. Returns `{"text_pages": [1,2,3,...], "image_pages": [4,5,6,...], "total_pages": N}`

#### 2B — Text extraction for selectable pages

Use `pdfplumber` for text-layer pages:

```python
import pdfplumber

def extract_text_page(pdf_path: str, page_num: int) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_num]
        text = page.extract_text(x_tolerance=3, y_tolerance=3)
        tables = page.extract_tables()
        # format tables as markdown
        return combine_text_and_tables(text, tables)
```

#### 2C — OCR extraction for image/non-selectable pages using Gemini 2.5 Flash

For pages that are scanned or image-based, use **Google Gemini 2.5 Flash** multimodal capability to:

1. Convert each PDF page to a high-resolution image (300 DPI using `pdf2image` / `PyMuPDF`)
2. Send the image to Gemini 2.5 Flash with a specific OCR prompt
3. Extract all text, equations (in LaTeX), tables, and diagram descriptions

```python
import google.generativeai as genai
from PIL import Image
import fitz  # PyMuPDF

genai.configure(api_key=settings.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

CHEMISTRY_OCR_PROMPT = """
You are a chemistry textbook OCR specialist. Extract ALL content from this page exactly as it appears.

Rules:
1. Extract all Arabic text verbatim — preserve Arabic script exactly
2. Convert all chemical equations to proper format: e.g. H₂O, CO₂, 2H₂ + O₂ → 2H₂O
3. Convert mathematical expressions to LaTeX: e.g. $E = mc^2$
4. Describe all diagrams, figures, and illustrations in detail: [DIAGRAM: description]
5. Extract tables as markdown format
6. Preserve section headings and sub-headings
7. Note page structure: headers, body text, examples, exercises
8. If there are colored boxes or highlighted sections, note them: [BOX: content]

Output format: plain text with the above conventions. Do not summarize — extract everything.
"""

async def ocr_page_with_gemini(pdf_path: str, page_num: int) -> str:
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    # Render at 300 DPI for high quality
    mat = fitz.Matrix(300/72, 300/72)
    pix = page.get_pixmap(matrix=mat)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    response = await model.generate_content_async([CHEMISTRY_OCR_PROMPT, img])
    return response.text
```

#### 2D — Full pipeline: extract → chunk → embed → store in pgvector

Create `app/services/ingestion_pipeline.py` with:

```python
async def run_full_ingestion(pdf_path: str, chapter_id: int | None = None):
    """
    Complete pipeline:
    1. Classify all pages (text vs image)
    2. Extract content from each page (pdfplumber or Gemini OCR)
    3. Split into semantic chunks (RecursiveCharacterTextSplitter)
    4. Embed each chunk with Google text-embedding-004
    5. Upsert into textbook_chunks table with pgvector
    """
```

Chunking strategy:

- Use `RecursiveCharacterTextSplitter` from LangChain
- `chunk_size=600` characters (shorter for Arabic — Arabic is denser)
- `chunk_overlap=80` characters
- Separators: `["\n\n", "\n", ".", "،", " "]` (include Arabic comma)
- Add metadata to each chunk: `page_number`, `chapter_id`, `source_type` (text/ocr), `extraction_method`

---

### TASK 3 — Embedding model: Google text-embedding-004

**Why Google text-embedding-004 and NOT OpenAI:**

- `text-embedding-004` outputs **768 dimensions** — smaller vectors = faster search, less storage
- **Excellent Arabic language support** — critical because the chemistry book is in Arabic
- Included in Google AI free tier / Gemini API — no extra API account needed
- Comparable quality to OpenAI ada-002 on retrieval benchmarks

Create `app/services/embeddings.py`:

```python
import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

async def embed_text(text: str) -> list[float]:
    """
    Embed a single text using Google text-embedding-004.
    Returns a 768-dimensional vector.
    """
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document",  # for chunked content
        title=None
    )
    return result["embedding"]  # list of 768 floats

async def embed_query(query: str) -> list[float]:
    """
    Embed a user query for similarity search.
    Use task_type="retrieval_query" — different from document embedding.
    """
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=query,
        task_type="retrieval_query"
    )
    return result["embedding"]

async def embed_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Embed multiple texts in batches to respect API rate limits.
    Google allows up to 100 texts per batch request.
    """
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=batch,
            task_type="retrieval_document"
        )
        all_embeddings.extend(result["embedding"])
    return all_embeddings
```

---

### TASK 4 — FastAPI routes for the ingestion pipeline

Create `app/api/ingestion.py` with these protected admin endpoints:

```
POST /admin/ingestion/start
    Body: { pdf_path: str, chapter_id: int | null }
    Starts the full ingestion pipeline as a Celery background task
    Returns: { task_id: str, status: "queued" }

GET  /admin/ingestion/status/{task_id}
    Returns the Celery task status and progress
    Returns: { status: "pending|processing|done|failed", progress: 0-100, chunks_created: int }

GET  /admin/ingestion/stats
    Returns: { total_chunks: int, chunks_by_chapter: {...}, avg_chunk_length: float, pages_processed: int }

DELETE /admin/ingestion/clear
    Deletes all textbook_chunks (for re-ingestion)
    Requires admin role

POST /admin/ingestion/test-chunk/{chunk_id}
    Tests that a specific chunk can be retrieved by similarity search
    Returns the chunk + its top-3 most similar chunks
```

All admin routes must be protected with an `is_admin` dependency.

---

### TASK 5 — RAG retrieval service

Create `app/services/rag.py`:

```python
async def retrieve_context(
    query: str,
    chapter_id: int | None = None,
    lesson_id: int | None = None,
    top_k: int = 5,
    min_similarity: float = 0.7
) -> list[RetrievedChunk]:
    """
    1. Embed the query using embed_query()
    2. Run pgvector cosine similarity search on textbook_chunks
    3. Filter by chapter_id or lesson_id if provided
    4. Filter by min_similarity threshold
    5. Return top_k chunks ordered by relevance score
    6. Cache result in Redis (key: hash(query + chapter_id), TTL: 1 hour)
    """
```

The pgvector SQL query:

```sql
SELECT id, content, source, page_number, chapter_id,
       1 - (embedding <=> $1::vector) AS similarity_score
FROM textbook_chunks
WHERE 1 - (embedding <=> $1::vector) > $2
  AND ($3::int IS NULL OR chapter_id = $3)
ORDER BY embedding <=> $1::vector
LIMIT $4;
```

---

### TASK 6 — Dependencies to add to requirements.txt

Add these packages (with pinned versions):

```
google-generativeai==0.8.3
pdfplumber==0.11.4
PyMuPDF==1.24.9
pdf2image==1.17.0
Pillow==10.4.0
langchain==0.3.7
langchain-community==0.3.7
langchain-google-genai==2.0.4
pgvector==0.3.2
celery[redis]==5.4.0
redis==5.1.1
```

---

### TASK 7 — Celery worker for background ingestion

Create `app/workers/ingestion_tasks.py`:

```python
from app.workers.celery_app import celery_app

@celery_app.task(bind=True, name="ingest_pdf")
def ingest_pdf_task(self, pdf_path: str, chapter_id: int | None = None):
    """
    Long-running Celery task that:
    1. Updates task state with progress (0% → 100%)
    2. Calls run_full_ingestion() with progress callbacks
    3. Reports chunks created, pages processed, errors per page
    4. Handles errors gracefully — one bad page should not stop the whole job
    """
```

---

### TASK 8 — Seed data script for interest_categories

Create `scripts/seed_interests.py`:

```python
INTEREST_CATEGORIES = [
    {"key": "football",    "name_ar": "كرة القدم",    "icon": "⚽", "order": 1},
    {"key": "volleyball",  "name_ar": "الكرة الطائرة", "icon": "🏐", "order": 2},
    {"key": "cooking",     "name_ar": "الطبخ",         "icon": "🍳", "order": 3},
    {"key": "cycling",     "name_ar": "الدراجة",        "icon": "🚴", "order": 4},
    {"key": "gaming",      "name_ar": "الألعاب",        "icon": "🎮", "order": 5},
    {"key": "music",       "name_ar": "الموسيقى",       "icon": "🎵", "order": 6},
    {"key": "art",         "name_ar": "الفن",           "icon": "🎨", "order": 7},
    {"key": "technology",  "name_ar": "التكنولوجيا",    "icon": "📱", "order": 8},
    {"key": "nature",      "name_ar": "الطبيعة",        "icon": "🌿", "order": 9},
    {"key": "movies",      "name_ar": "الأفلام",        "icon": "🎬", "order": 10},
    {"key": "travel",      "name_ar": "السفر",          "icon": "✈️", "order": 11},
    {"key": "fitness",     "name_ar": "الرياضة",        "icon": "💪", "order": 12},
]
```

Run with: `python scripts/seed_interests.py`

---

## 🗂️ FILES TO ATTACH WHEN SENDING THIS PROMPT

Attach all of these to the Copilot/Cursor context:

1. `docs/erd-diagram.md` — the full ERD
2. `app/core/config.py` — settings file (so Copilot knows your env vars)
3. `app/models/` — entire folder (so Copilot knows what already exists)
4. `app/api/` — entire folder (so Copilot follows your existing route patterns)
5. `requirements.txt` — current dependencies
6. `docker-compose.yml` — so Copilot knows your service names and ports
7. `alembic.ini` — migration config

---

## ✅ DEFINITION OF DONE

You are finished when:

- [ ] All 20+ models exist in `app/models/` with full type annotations
- [ ] Alembic migration runs cleanly: `alembic upgrade head` with zero errors
- [ ] `textbook_chunks.embedding` is `VECTOR(768)` with an ivfflat index
- [ ] `scripts/ingest_pdf.py` runs and produces chunks in the DB
- [ ] `scripts/seed_interests.py` runs and inserts all 12 categories
- [ ] `app/services/embeddings.py` embeds Arabic text correctly
- [ ] `app/services/rag.py` retrieves relevant chunks for a test query
- [ ] `app/services/pdf_processor.py` classifies pages and runs OCR on image pages
- [ ] All new routes appear in `/docs` (Swagger)
- [ ] No `import` errors when starting `uvicorn app.main:app --reload`

---

## ⚠️ HARD RULES — DO NOT VIOLATE THESE

1. **NEVER use OpenAI embeddings** — use Google `text-embedding-004` only
2. **NEVER use `VECTOR(1536)`** — the dimension MUST be `768`
3. **ALL database calls must be async** — use `await session.execute(...)` not `session.execute(...)`
4. **ALL models must use `SQLModel`** — not raw SQLAlchemy `Base`
5. **ALL API endpoints must have Pydantic request/response schemas** — no `dict` returns
6. **Handle Arabic text correctly** — ensure UTF-8 encoding everywhere, do NOT transliterate
7. **Every service function must have a docstring** explaining what it does
8. **Every new file must have a module-level docstring** at the top
9. **Do NOT hardcode API keys** — always read from `settings.GEMINI_API_KEY`, `settings.ANTHROPIC_API_KEY`
10. **Run `ruff check .` before finishing** — zero linting errors allowed
