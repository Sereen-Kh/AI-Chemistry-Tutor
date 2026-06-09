# 🧠 EduMind: System Architecture, ML Models & ORM Reference

This document provides a production-grade overview of the system architecture of the **EduMind Chemistry Tutor** application. It serves as the primary technical reference for the AI & Machine Learning pipeline, the relational database schema (SQLAlchemy ORM), and the backend service APIs.

---

## 🤖 1. AI & Machine Learning Models (LLMs & Embeddings)

All server-side AI interactions are centrally configured in [config.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/core/config.py) and initialized in [gemini_client.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/gemini_client.py).

### A. Tutoring Chat & Homework Solver
* **Primary Model:** `gemini-3.5-flash` (via `model_name` config)
* **Configuration:**
  * **Temperature:** `0.4` (Tuned in `tutor_generation_config` to balance pedagogical friendliness with strict chemical accuracy).
  * **Max Output Tokens:** `1024` tokens.
  * **System Instruction:** Injects a strict Arabic-focused tutor persona named **EduMind** who guides Grade 9 students step-by-step.
  * **LaTeX Formatting Constraint:** Strictly forbids formatting inline formulas using LaTeX math notation (e.g., `$\text{CO}_2$`) to ensure compatibility and legibility on mobile/web viewports, enforcing standard unicode subscripts (e.g., `CO₂`, `H₂O`).
* **Use Cases:** Conversational RAG tutoring, stateless Q&A, and homework math solving.

### B. Structured Document Extraction & OCR
* **Primary Model:** `gemini-3-flash-preview` or `gemini-3.5-flash` (via `gemini_document_model` config)
* **Configuration:**
  * **Temperature:** `0.0` (Ensures maximum schema adherence).
  * **Max Output Tokens:** `8192` tokens.
  * **Response Format:** Enforced JSON schema using Pydantic (`PageExtractionResult`).
  * **Fallback OCR Model:** `gemini-2.5-pro` or `gemini-3.1-flash-lite` (via `gemini_document_fallback_model`). Activated automatically if the primary model fails quality/completeness checks during parsing.
* **Use Cases:** Digitizing textbook chapters, tables, chemistry equations, exercises, and diagrams.

### C. Text & Query Embeddings
* **Primary Model:** `gemini-embedding-001` or `text-embedding-004` (via `gemini_embedding_model` config)
* **Configuration:**
  * **Task Types:** `RETRIEVAL_DOCUMENT` for chunk generation (indexing), `RETRIEVAL_QUERY` for queries (search).
  * **Dimensionality:** `768` dimensions.
* **Local Fallback Model:** `intfloat/multilingual-e5-base` (via `sentence-transformers`) generating a `768-dim` vector (prepends `"query: "` / `"passage: "` for E5 task-specific compatibility).
* **Offline Development Fallback:** Local SHA-256 hash-based vectorizer generating deterministic normalized mock vectors of `768` dimensions.

---

## 🗄️ 2. Project Database Entities (SQLAlchemy ORM Schemas)

The database layers are implemented using SQLAlchemy 2.0 async mapped columns and are managed in [app/models/](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models).

### A. User Management & Onboarding
* **`User`** ([user.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/user.py)): Stores student credentials, streak records, gamification scores (XP, Level), and active tutoring parameters.
* **`StudentProfile`** ([student_profile.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/student_profile.py)): Holds learning preferences (teaching style, answer format, goals) resolved during onboarding.
* **`InterestCategory`** ([interest.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/interest.py)): Predefined lists of interests (e.g. video games, space) used by Gemini to formulate analogy-based explanations.
* **`UserInterest`** ([interest.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/interest.py)): Junction table mapping Users to Interest Categories.

### B. Curriculum Structures
* **`Chapter`** ([chemistry.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py)): Outlines syllabus chapters (order, title in Arabic/English, description).
* **`Lesson`** ([chemistry.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py)): Stores the markdown content of lessons associated with a specific chapter.
* **`Topic`** ([topic.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/topic.py)): Groups related lesson pages together to support spaced repetition review.

### C. Ingestion & Vector Storage (RAG)
* **`ContentSource`** ([textbook.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py)): Meta-registry for files parsed by the pipeline (e.g., standard textbooks, solved chemistry answer booklets).
* **`RagChunk`** ([textbook.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py)): Stores chunk content, normalized Arabic strings for lexical lookups, metadata JSON (cache path, warnings), and a `pgvector` `Vector(768)` column indexed using `ivfflat` with `vector_cosine_ops` (fallback to SQLite JSON column locally).
* **`ExtractedQuestion`** ([textbook.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py)): Seeded and AI-extracted multiple-choice and short-answer questions verified through a human-in-the-loop audit flag (`needs_review`).
* **`IngestionJob`** ([ingestion.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/ingestion.py)): Logs Celery/FastAPI background tasks running parsing pipelines.
* **`IngestionPage`** ([ingestion.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/ingestion.py)): Logs per-page OCR quality audit metrics (completeness score, char count, errors).

### D. Chat & Interactions
* **`ChatSession`** ([chat.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chat.py)): Maps active multi-turn chats to specific lessons and students.
* **`ChatMessage`** ([chat.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chat.py)): Individual question/answer turns with latency trackers and user feedback flags.
* **`Homework`** ([homework.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/homework.py)): Tracks typed or photo-uploaded student questions, storing OCR-extracted text, RAG source chunks, and step-by-step solutions.

### E. Assessments & Spaced Repetition
* **`Question`** ([assessment.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/assessment.py)): Seeds multiple-choice quizzes.
* **`QuizAttempt`** / **`QuestionAttempt`** ([assessment.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/assessment.py)): Tracks quiz scores and individual attempts to gauge a user's weak points.
* **`Flashcard`** / **`FlashcardProgress`** ([flashcard.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/flashcard.py)): Supports spaced repetition card reviews scheduled via the SM-2 algorithm (`ease_factor`, `interval_days`, `next_review_at`).
* **`StudyPlan`** ([study_plan.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/study_plan.py)): Stores structured day-by-day learning tasks dynamically mapped to target exam dates.

---

## 📞 3. External AI API Call Map

The backend performs **7 distinct integrations** with the Google Gemini API:

| # | Feature | File Location | API Method | Model | Sync/Async | Fallback Behavior |
|---|---------|---------------|------------|-------|------------|-------------------|
| 1 | Tutor Chat | [ai_service.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ai_service.py#L59) | `models.generate_content` | `gemini-3.5-flash` | Async | Lexical fallback extraction (`_local_rag_answer`) |
| 2 | Document Indexing | [embeddings.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L37) | `models.embed_content` (`RETRIEVAL_DOCUMENT`) | `gemini-embedding-001` | Async | `multilingual-e5-base` / Hash vectorizer |
| 3 | Query Embedding | [embeddings.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py#L61) | `models.embed_content` (`RETRIEVAL_QUERY`) | `gemini-embedding-001` | Async | `multilingual-e5-base` / Hash vectorizer |
| 4 | Primary PDF Extraction | [gemini_provider.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L133) | `models.generate_content` (JSON schema mode) | `gemini-3-flash-preview` | Async | Route fallback model chain |
| 5 | Fallback OCR Routing | [gemini_provider.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L193) | `models.generate_content` (JSON schema mode) | `gemini-3.1-flash-lite` | Async | Raises quality validation error |
| 6 | Files API upload | [gemini_provider.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L248) | `files.upload` | N/A | Async | Renders PDF pages to images locally |
| 7 | Image OCR Fallback | [gemini_provider.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L337) | `models.generate_content` (PNG bytes) | Same model chain | Async | Traditional PDF text layer fallback |

---

## ⚡ 4. Semantic RAG Pipeline & Retrieval Flow

The hybrid RAG engine is managed in [rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py) and [semantic_rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/semantic_rag.py).

```
[User Query]
    │
    ├──► 1. clean_query()         (Removes conversational Arabic noise phrases)
    │
    ├──► 2. rewrite_query()       (Rewrites & expands with Arabic chemical synonyms)
    │
    ├──► 3. _query_terms()        (Normalizes Arabic, tokenizes, strips prefixes/suffixes)
    │
    ├──► 4. embed_query()         (Generates 768-dim vector using gemini-embedding-001)
    │
    ├──► 5. Redis Cache Check     (Key: "rag_cache:v6:<filters_md5>", TTL: 1 hr)
    │        ├── [HIT]  ──► Return Cached RetrievedChunk list
    │        └── [MISS] ──► Query Database
    │
    ├──► 6. Vector Database Query
    │        ├── PostgreSQL: pgvector similarity query (ordering by cosine distance)
    │        └── SQLite: Load all candidate vectors, compute cosine similarity in Python
    │
    ├──► 7. Hybrid Scoring & Boosting (Blends: 0.35 * Vector Similarity + 0.65 * Lexical Score)
    │        ├── +0.18 for specific definition/equation intent matches
    │        ├── +0.10 for chemical formula exact substring hits (e.g., HCl, CO₂)
    │        └── Up to +0.70 for acid-metal reaction intents (e.g., Dilute Acid + Metal)
    │
    ├──► 8. Threshold & Slice     (Filter by min_similarity, sort desc, select top_k)
    │
    ├──► 9. Reranker Model        (Cross-Encoder reranking using gemini-2.0-flash)
    │
    └──► 10. Redis Cache Store    (Save serialized results to Cache)
```

### Deterministic & Chemistry Rule Fallbacks
Before performing vector search, the chat handler in `chat_service.py` runs three deterministic checks:
1. **Approved Dictionary Entry Lookup:** If the query matches an approved chemical entity alias (defined in [chemistry_entities.json](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/rag/data/chemistry_entities.json)) and the intent is a simple lookup, it returns the static dictionary definition immediately.
2. **Metal-Acid Reaction Engine:** Identifies reactants (e.g. `Zn + HCl` or `Fe + H2SO4`) and returns the balanced equation and activity series outcome without executing a RAG/LLM call.
3. **Stateless Query Router:** Direct navigation checks (e.g. requests for page numbers or syllabus topics).

---

## 🛠️ 5. API Endpoint Architecture

### A. Chat & Tutoring Endpoint Spec
#### `POST /api/v1/chat/ask`
Stateless API responding with context-grounded tutor answers.
* **Request Payload:**
  ```json
  {
    "question": "احسب عدد أيونات H+ في HCl من كتاب الحلول صفحة 117",
    "lesson_id": 3,
    "topic_id": 12,
    "source_types": ["solutions"],
    "preferred_answer_type": "text",
    "answer_scope": "auto"
  }
  ```
* **Response Payload (ChatAnswerResponse):**
  ```json
  {
    "answer": "صيغة حمض كلور الماء هي HCl، وعند تأينه في الماء يعطي أيون هيدروجين واحد H⁺ لكل صيغة أيونية...",
    "answer_type": "text",
    "route": "textbook_rag",
    "grounding": "book",
    "answer_scope": "auto",
    "blocks": [
      {
        "type": "text",
        "content": "صيغة حمض كلور الماء...",
        "page": 117,
        "image_url": null,
        "metadata": {}
      }
    ],
    "sources": [
      {
        "chunk_id": 1358,
        "source_id": 2,
        "source": "Solutions_Chemistry",
        "page_number": 51,
        "content_type": "definition",
        "similarity_score": 0.784
      }
    ],
    "source_blocks": [
      {
        "book_id": "Solutions_Chemistry",
        "page": 51,
        "chunk_id": 1358,
        "chunk_type": "definition",
        "score": 0.784
      }
    ],
    "page_numbers": [51],
    "confidence": 0.784,
    "diagnostics": {
      "original_query": "احسب عدد أيونات H+...",
      "intent": "book_grounded",
      "entity": "hydrochloric_acid",
      "top_score": 0.784,
      "source_route": {
        "route": "solutions",
        "source_types": ["solutions"],
        "reason": "solution_or_calculation_keywords"
      }
    },
    "suggested_next_action": "جرّب سؤالاً تدريبياً مرتبطاً بالمصدر."
  }
  ```

### B. Homework Solver Endpoint Spec
#### `POST /api/v1/homework/solve-image`
Processes photos of student homework, running OCR and formulating solutions grounded in textbook context.
* **Request Payload (Multipart Form):**
  * `file`: Uploaded homework image.
  * `topic_id`: Optional topic filter.
* **Response Payload (HomeworkResponse):**
  ```json
  {
    "id": 19,
    "user_id": 3,
    "topic_id": 5,
    "image_url": "/data/uploads/homework_image_01.png",
    "problem_text": "احسب عدد مولات 10 غرام من NaOH",
    "extracted_text": "احسب عدد مولات 10 غرام من NaOH",
    "solution": "لحل هذه المسألة:\nالكتلة المولية لـ NaOH = 23 + 16 + 1 = 40 g/mol.\nعدد المولات = الكتلة / الكتلة المولية = 10 / 40 = 0.25 mol.",
    "source_chunks": null,
    "confidence_score": 0.8,
    "created_at": "2026-06-08T09:20:00Z",
    "updated_at": "2026-06-08T09:20:00Z"
  }
  ```

### C. Ingestion & Search Endpoint Spec
#### `POST /api/v1/rag/retrieve`
Core RAG retrieval engine accepting filters and returning matching chunk lists.
* **Request Payload:**
  ```json
  {
    "query": "ما هي الحموض؟",
    "chapter_id": 1,
    "lesson_id": 3,
    "top_k": 5,
    "min_similarity": 0.25
  }
  ```
* **Response Payload:**
  ```json
  {
    "chunks": [
      {
        "id": 145,
        "source_id": 1,
        "content": "الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهيدروجين.",
        "source": "syria_grade_9_chemistry",
        "source_type": "textbook",
        "content_type": "text",
        "page_number": 11,
        "chapter_id": 1,
        "lesson_id": 3,
        "topic_id": 12,
        "metadata_json": {
          "extraction_methods": ["pymupdf", "gemini_pdf_file"]
        },
        "similarity_score": 0.812
      }
    ]
  }
  ```
