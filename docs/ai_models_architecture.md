# 🧠 EduMind Model Architecture Reference

This document provides a detailed overview of both the **AI & Machine Learning Models** (LLM & Embeddings) and the **Database ORM Models** (SQLAlchemy Schema) used within the EduMind Chemistry Tutor system.

---

## 🤖 1. AI & Machine Learning Models (RAG & LLM Engine)

These models are configured centrally within [config.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/core/config.py) and instantiated server-side via [gemini_client.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/gemini_client.py).

### A. Conversational Tutoring & Homework Solver
*   **Primary Model:** `gemini-3.5-flash` (configured via `model_name` in [Settings](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/core/config.py#L12)).
*   **Properties & Options:**
    *   **Temperature:** `0.4` (Tuned in [tutor_generation_config](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/gemini_client.py#L40) to balance precise chemical accuracy with engaging, friendly pedagogy).
    *   **Max Output Tokens:** `1024` tokens.
    *   **System Prompt:** Dynamic Arabic (`ar`) prompt defining the persona of **EduMind**, a Grade 9 Chemistry tutor who uses textbook context when available, defaulting to short general explanations when missing.
*   **Use Cases:** Multi-turn tutoring chats, stateless chemistry questions, step-by-step homework resolution, and quiz/flashcard/study-plan generation.

### B. Structured Page Extraction & OCR
*   **Primary Model:** `gemini-3.5-flash` or `gemini-3-flash-preview` (configured via `gemini_document_model` in [config.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/core/config.py#L23)).
*   **Properties & Options:**
    *   **Temperature:** `0.0` (Tuned in [document_generation_config](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/gemini_client.py#L27) for high structured format adherence).
    *   **Max Output Tokens:** `8192` tokens.
    *   **Response Mode:** Strict JSON output matching a Pydantic schema (`PageExtractionResult`).
    *   **Fallback OCR Model:** `gemini-2.5-pro` or `gemini-3.1-flash-lite` (via `gemini_document_fallback_model`). Utilized automatically in [gemini_provider.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/gemini_provider.py#L193) if primary extraction fails quality or completeness checks.
*   **Use Cases:** Parsing Grade 9 Arabic Chemistry textbook PDFs into structured markdown sections, tables, equations, diagram descriptions, and textbook quiz questions.

### C. Text & Query Embedding Models
*   **Primary Model:** `gemini-embedding-001` or `text-embedding-004` (via `gemini_embedding_model`).
*   **Properties:**
    *   **Dimensionality:** `768` dimensions.
    *   **Task Types:** 
        *   `RETRIEVAL_DOCUMENT` for textbook chunk generation (indexing).
        *   `RETRIEVAL_QUERY` for embedding user queries (search).
*   **Local Fallback Model:** `intfloat/multilingual-e5-base` (via `sentence-transformers`).
    *   **Dimensionality:** `768` dimensions.
    *   **Task Formatting:** Prepends query strings with `"query: "` and passage chunks with `"passage: "` for E5 compatibility.
*   **Local Dev Fallback (Offline Mode):** Local hash-based SHA-256 vectorizer generating a normalized `768-dim` mock vector (ensures code runs in development environments when API credentials are absent).

---

## 🗄️ 2. Database ORM Models (SQLAlchemy & pgvector)

These models define the relational schema stored in PostgreSQL, with vector column search powered by `pgvector`. A diagram of these relations is located in [erd-diagram.md](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/docs/erd-diagram.md).

### A. RAG & Textbook Ingestion Engine
Defined in [textbook.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py):

*   **[ContentSource](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L41) (`content_sources` table):**
    *   `id` (int, PK)
    *   `source_type` (str): e.g., textbook, exam, key.
    *   `title` (str)
    *   `grade` (str)
    *   `subject` (str)
    *   `year` (int, nullable)
    *   `file_path` (str, nullable)
    *   `status` (str): e.g., pending, completed.
    *   `metadata_json` (JSON)
*   **[RagChunk](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L63) (`rag_chunks` table):**
    *   `id` (int, PK)
    *   `source_id` (int, FK)
    *   `chapter_id` / `lesson_id` / `topic_id` (int, FK, nullable)
    *   `page_number` (int, nullable)
    *   `chunk_index` (int)
    *   `content` (text)
    *   `normalized_content` (text, nullable)
    *   `content_type` (str): e.g., text, table, equation.
    *   `source_type` (str)
    *   `embedding` (vector, 768-dim)
    *   `metadata_json` (JSON)
*   **[ExtractedQuestion](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L114) (`extracted_questions` table):**
    *   `id` (int, PK)
    *   `source_id` (int, FK)
    *   `chapter_id` / `lesson_id` / `topic_id` (int, FK, nullable)
    *   `question_text` (text)
    *   `options` (JSON)
    *   `correct_answer` (text, nullable)
    *   `explanation` (text, nullable)
    *   `needs_review` (bool, default True)

### B. User Profile & Preferences
Defined in [user.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/user.py):

*   **[User](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/user.py#L14) (`users` table):**
    *   `id` (int, PK)
    *   `first_name` (str)
    *   `last_name` (str)
    *   `email` (str, unique)
    *   `phone` (str, nullable)
    *   `hashed_password` (str)
    *   `grade` / `subject` (str)
    *   `teaching_style` (str): e.g., real-life, scientific, step-by-step.
    *   `answer_format` (str): e.g., text, text+image.
    *   `language` (str): default `ar` (Arabic).
    *   `xp` / `level` / `streak_days` (int)
    *   `last_active_date` (date, nullable)

### C. AI Chat & Conversations
Defined in [chat.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chat.py):

*   **[ChatSession](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chat.py#L10) (`chat_sessions` table):**
    *   `id` (int, PK)
    *   `user_id` (int, FK)
    *   `lesson_id` (int, FK, nullable)
    *   `title` (str, nullable)
    *   `style` (str, nullable)
*   **[ChatMessage](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chat.py#L32) (`chat_messages` table):**
    *   `id` (int, PK)
    *   `session_id` (int, FK)
    *   `role` (str): e.g., user, assistant.
    *   `content` (text)
    *   `format` (str): e.g., text, image.
    *   `feedback` (str, nullable): e.g., understood, not_understood.
    *   `latency_ms` (int, nullable)

### D. Curriculum, Assessments & Gamification
Other models in the schema:
*   `Chapter` & `Lesson`: Textbook hierarchy structure.
*   `Topic`: High-level curriculum concepts matching question banks.
*   `Question` & `QuizAttempt`: Seeded/generated questions and student attempts.
*   `Flashcard` & `FlashcardProgress`: Study terms and Leitner system progress.
*   `StudyPlan`: Custom personalized day-by-day learning assignments.
*   `Homework`: Image/text assignments and generated solutions.
*   `Achievement`: Earned rewards and unlocking rules.
