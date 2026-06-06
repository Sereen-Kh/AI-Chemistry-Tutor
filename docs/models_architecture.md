# 🧠 EduMind Model & Entity Architecture Reference

This document provides a detailed overview of the system architecture, detailing both **AI & Machine Learning Models** (LLMs & Embeddings) and **Database ORM Entities** (SQLAlchemy Schema) used within the EduMind Chemistry Tutor system.

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

## 🗄️ 2. Project Database Entities (SQLAlchemy ORM Schema)

This section maps every entity implemented in the database, grouped by architectural subsystem. A database relationships summary is available in [erd-diagram.md](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/docs/erd-diagram.md).

### Module A: User Management & Onboarding
These entities represent student authentication, settings, metadata, and custom personalization hooks.

#### 1. [User](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/user.py#L14) (`users` table)
Defined in [user.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/user.py). Stores core credentials alongside active tutoring preferences and gamification metrics.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `first_name` (String(100), Nullable=False)
    *   `last_name` (String(100), Default="")
    *   `email` (String(255), Unique, Indexed, Nullable=False)
    *   `phone` (String(30), Nullable=True)
    *   `hashed_password` (String, Nullable=False)
    *   `email_verified` (Boolean, Default=False)
    *   `grade` (String(50), Default="grade_9")
    *   `subject` (String(50), Default="chemistry")
    *   `teaching_style` (String(50)): Real-life analogies, scientific, or step-by-step.
    *   `answer_format` (String(50)): Text, text+image, text+voice.
    *   `language` (String(8), Default="ar")
    *   `xp` (Integer, Default=0)
    *   `level` (Integer, Default=1)
    *   `streak_days` (Integer, Default=0)
    *   `last_active_date` (Date, Nullable=True)
*   **Relationships:**
    *   `interests` $\to$ Many `UserInterest`
    *   `student_profile` $\to$ One `StudentProfile`
    *   `chat_sessions` $\to$ Many `ChatSession`
    *   `homework_items` $\to$ Many `Homework`

#### 2. [StudentProfile](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/student_profile.py#L13) (`student_profiles` table)
Defined in [student_profile.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/student_profile.py). Holds extended onboarding data to drive persona adjustments for the tutor.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Unique, Indexed)
    *   `grade` (String(50), Default="grade_9")
    *   `subject` (String(80), Default="chemistry")
    *   `learning_style` (String(80)): Personalization profile.
    *   `preferred_language` (String(8), Default="ar")
    *   `goals` (Text, Nullable=True): Free-text student learning goals.
    *   `target_exam_date` (Date, Nullable=True)
    *   `metadata_json` (JSON, Nullable=True)
*   **Relationships:**
    *   `user` $\to$ Link back to `User`

#### 3. [InterestCategory](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/interest.py#L11) (`interest_categories` table)
Defined in [interest.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/interest.py). Predefined list of student interests (e.g. Sports, Space, Video Games) used by the LLM to generate analogies.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `key` (String(80), Unique, Indexed, Nullable=False): Identifier slug.
    *   `name_ar` (String(120), Nullable=False)
    *   `name_en` (String(120), Nullable=True)
    *   `icon` (String(40), Nullable=True): Emojis or asset paths.
    *   `display_order` (Integer, Default=0)
*   **Relationships:**
    *   `users` $\to$ Many `UserInterest`

#### 4. [UserInterest](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/interest.py#L27) (`user_interests` table)
Defined in [interest.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/interest.py). Junction table enabling a Many-to-Many mapping between Users and Interest Categories.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed)
    *   `interest_id` (Integer, ForeignKey("interest_categories.id"), Indexed)

---

### Module B: Chemistry Curriculum & Reference
These entities model the formal structure of the Syrian Grade 9 Chemistry curriculum and static scientific lookup tables.

#### 5. [Element](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py#L13) (`elements` table)
Defined in [chemistry.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py). Lookup data for the periodic table.
*   **Properties:**
    *   `atomic_number` (Integer, Primary Key)
    *   `symbol` (String(4), Unique, Indexed, Nullable=False): e.g., "Fe", "O".
    *   `name_ar` / `name_en` (String(80), Nullable=False)
    *   `atomic_mass` (Float, Nullable=True)
    *   `category` (String(80)): e.g., Transition Metal.
    *   `period` / `group` (Integer, Nullable=True)
    *   `electron_configuration` (Text, Nullable=True)

#### 6. [Chapter](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py#L29) (`chapters` table)
Defined in [chemistry.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py). Stores high-level curriculum chapters.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `title_ar` (String(255), Nullable=False)
    *   `title_en` (String(255), Nullable=True)
    *   `description_ar` (Text, Nullable=True)
    *   `order` (Integer, Default=0, Indexed, Nullable=False)
    *   `difficulty` (Integer, Default=1)
    *   `icon` (String(80), Nullable=True)
*   **Relationships:**
    *   `lessons` $\to$ Many `Lesson`
    *   `rag_chunks` $\to$ Many `RagChunk`

#### 7. [Lesson](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py#L47) (`lessons` table)
Defined in [chemistry.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py). Stores specific lessons under each chapter containing markdown curriculum content.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `chapter_id` (Integer, ForeignKey("chapters.id"), Indexed)
    *   `title_ar` (String(255), Nullable=False)
    *   `title_en` (String(255), Nullable=True)
    *   `content_ar` (Text, Default="")
    *   `order` (Integer, Default=0, Indexed)
    *   `difficulty` (Integer, Default=1)
    *   `duration_min` (Integer, Default=10): Estimated reading time.
*   **Relationships:**
    *   `chapter` $\to$ Belongs to `Chapter`
    *   `progress_records` $\to$ Many `LessonProgress`
    *   `rag_chunks` $\to$ Many `RagChunk`

#### 8. [Topic](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/topic.py#L10) (`topics` table)
Defined in [topic.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/topic.py). Curricular subjects used to group assessment items like flashcards, homework questions, and quizzes.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `title_ar` (String(255), Nullable=False)
    *   `title_en` (String(255), Nullable=True)
    *   `description_ar` (Text, Nullable=True)
    *   `category` (String(80)): e.g. Organic, Inorganic, Physical, Analytical.
    *   `difficulty` (Integer, Default=1)
    *   `icon` (String(80), Nullable=True)
    *   `order` (Integer, Default=0, Indexed)
*   **Relationships:**
    *   `questions` $\to$ Many `Question`
    *   `flashcards` $\to$ Many `Flashcard`
    *   `quiz_attempts` $\to$ Many `QuizAttempt`
    *   `extracted_questions` $\to$ Many `ExtractedQuestion`

---

### Module C: Textbook Ingestion & RAG (Vector Search)
These entities back the ingestion pipeline, mapping OCR runs and chunks of textbook content with their multi-dimensional embeddings.

#### 9. [ContentSource](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L41) (`content_sources` table)
Defined in [textbook.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py). Metadata registry for textbooks, mock exams, or manuals being indexed.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `source_type` (String(40), Indexed, Nullable=False): e.g., "textbook", "exam".
    *   `title` (String(255), Nullable=False)
    *   `grade` (String(50), Default="grade_9")
    *   `subject` (String(80), Default="chemistry")
    *   `year` (Integer, Nullable=True, Indexed)
    *   `file_path` (String(500), Nullable=True): Local storage URI.
    *   `original_filename` (String(255), Nullable=True)
    *   `status` (String(40), Default="pending", Indexed): Ingestion status.
    *   `metadata_json` (JSON, Nullable=True)
*   **Relationships:**
    *   `chunks` $\to$ Many `RagChunk` (Cascaded deletion)
    *   `extracted_questions` $\to$ Many `ExtractedQuestion` (Cascaded deletion)

#### 10. [RagChunk](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L63) (`rag_chunks` table)
Defined in [textbook.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py). Ground-truth database vector store. Integrates `pgvector` for search operations.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `source_id` (Integer, ForeignKey("content_sources.id"), Nullable=False)
    *   `chapter_id` / `lesson_id` / `topic_id` (Integer, ForeignKey, Nullable=True)
    *   `page_number` (Integer, Nullable=True, Indexed)
    *   `chunk_index` (Integer, Nullable=False): Sequential index in PDF.
    *   `content` (Text, Nullable=False): Raw text slice.
    *   `normalized_content` (Text, Nullable=True): Arabic text normalized for search matching.
    *   `content_type` (String(40), Default="text"): e.g. text, table, diagram, equation.
    *   `source_type` (String(40), Default="textbook")
    *   `extraction_method` (String(80), Default="pdf_text")
    *   `language` (String(8), Default="ar")
    *   `embedding` (Vector(768), Nullable=True): 768-dim embedding array.
    *   `metadata_json` (JSON, Nullable=True)
*   **Indices:**
    *   Indexed by `embedding` using `ivfflat` with `vector_cosine_ops`.
    *   Foreign key links indexed for fast filtered-retrieval.

#### 11. [ExtractedQuestion](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L114) (`extracted_questions` table)
Defined in [textbook.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py). Question structures extracted from documents during ingestion.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `source_id` (Integer, ForeignKey("content_sources.id"), Nullable=False)
    *   `chapter_id` / `lesson_id` / `topic_id` (Integer, ForeignKey, Nullable=True)
    *   `page_number` (Integer, Nullable=True)
    *   `question_text` (Text, Nullable=False)
    *   `question_type` (String(40), Default="unknown")
    *   `options` (JSON, Nullable=True): List of options.
    *   `correct_answer` (Text, Nullable=True)
    *   `explanation` (Text, Nullable=True)
    *   `answer_source` (String(40), Default="unknown")
    *   `difficulty` (Integer, Nullable=True)
    *   `needs_review` (Boolean, Default=True, Indexed): Human-in-the-loop audit flag.
    *   `metadata_json` (JSON, Nullable=True)

#### 12. [IngestionJob](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/ingestion.py#L10) (`ingestion_jobs` table)
Defined in [ingestion.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/ingestion.py). Tracks asynchronous Celery ingestion tasks.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `job_uid` (String(64), Unique, Indexed, Nullable=False): UUID reference.
    *   `source_id` (Integer, ForeignKey("content_sources.id"), Nullable=True, Indexed)
    *   `status` (String(40), Default="queued", Indexed): queued, running, completed, failed.
    *   `progress` (Integer, Default=0): Percent completed.
    *   `message` (String(255), Nullable=True)
    *   `result_json` (JSON, Nullable=True)
    *   `errors_json` (JSON, Nullable=True)

#### 13. [IngestionPage](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/ingestion.py#L29) (`ingestion_pages` table)
Defined in [ingestion.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/ingestion.py). Detailed per-page ingestion logs for quality gate audits.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `source_id` (Integer, ForeignKey("content_sources.id"), Indexed, Nullable=False)
    *   `job_id` (Integer, ForeignKey("ingestion_jobs.id"), Nullable=True)
    *   `page_number` (Integer, Indexed, Nullable=False)
    *   `page_type` (String(40), Nullable=False): e.g., introduction, lesson_body, exercises.
    *   `status` (String(40), Default="pending", Indexed)
    *   `extraction_methods` (JSON, Nullable=True)
    *   `cache_path` (String(500), Nullable=True): Path to rendered page images.
    *   `char_count` (Integer, Default=0)
    *   `completeness_score` (Float, Default=0.0): Extracted info completeness metric (0.0 to 1.0).
    *   `warnings_json` / `errors_json` (JSON, Nullable=True)
    *   `content_preview` (Text, Nullable=True)

#### 14. [TextbookChunk](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py#L22) (`textbook_chunks` table)
Defined in [textbook.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/textbook.py). Kept for legacy schema compatibility.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `chapter_id` (Integer, ForeignKey("chapters.id"), Nullable=True)
    *   `page_number` (Integer, Nullable=True)
    *   `content` (Text, Nullable=False)
    *   `source` (String(255), Nullable=True)
    *   `source_type` (String(40), Nullable=True)
    *   `extraction_method` (String(80), Nullable=True)
    *   `embedding` (Vector(768) or JSON, Nullable=True)

---

### Module D: Tutoring Sessions & AI Interactions
These entities persist ongoing interactions between the tutor agent and students.

#### 15. [ChatSession](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chat.py#L10) (`chat_sessions` table)
Defined in [chat.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chat.py). Root container for a conversation.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed, Nullable=False)
    *   `lesson_id` (Integer, ForeignKey("lessons.id"), Nullable=True, Indexed)
    *   `title` (String(255), Nullable=True): Summarized topic of session.
    *   `style` (String(50), Nullable=True): Teaching style override.
*   **Relationships:**
    *   `messages` $\to$ Many `ChatMessage` (Ordered by time)

#### 16. [ChatMessage](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chat.py#L32) (`chat_messages` table)
Defined in [chat.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chat.py). One message turn.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `session_id` (Integer, ForeignKey("chat_sessions.id"), Indexed, Nullable=False)
    *   `role` (String(20), Nullable=False): "user" or "assistant".
    *   `content` (Text, Nullable=False): Message body.
    *   `format` (String(20), Default="text"): text, image, voice, video.
    *   `feedback` (String(30), Nullable=True): understood, not_understood.
    *   `media_url` (String(500), Nullable=True): URL to uploaded student image or audio response.
    *   `latency_ms` (Integer, Nullable=True): Latency of the model request.

#### 17. [Homework](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/homework.py#L10) (`homework` table)
Defined in [homework.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/homework.py). Persists uploaded homework questions.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed, Nullable=False)
    *   `topic_id` (Integer, ForeignKey("topics.id"), Nullable=True, Indexed)
    *   `image_url` (String(500), Nullable=True): Student photograph of paper homework.
    *   `problem_text` (Text, Nullable=False): Extracted text query or transcription.
    *   `extracted_text` (Text, Nullable=True): Raw OCR output from input image.
    *   `solution` (Text, Default=""): AI-generated step-by-step math/chemical explanation.
    *   `source_chunks` (JSON, Nullable=True): RAG chunks used as sources for citation.
    *   `confidence_score` (Float, Nullable=True)

---

### Module E: Assessment, Scheduling & Spaced Repetition
These entities organize personalized quizzes, study paths, and flashcards using spaced repetition scheduling.

#### 18. [Question](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/assessment.py#L13) (`questions` table)
Defined in [assessment.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/assessment.py). Seeded multiple-choice quizzes.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `topic_id` (Integer, ForeignKey("topics.id"), Indexed, Nullable=False)
    *   `question_ar` (Text, Nullable=False)
    *   `options` (JSON, Nullable=False): List of possible answers.
    *   `correct_answer` (Integer, Nullable=False): Options index.
    *   `explanation_ar` (Text, Nullable=True)
    *   `difficulty` (Integer, Default=1)
    *   `source` (String(40), Default="seeded"): seeded, ai_generated.

#### 19. [QuizAttempt](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/assessment.py#L30) (`quiz_attempts` table)
Defined in [assessment.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/assessment.py). Stores complete quiz results.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed, Nullable=False)
    *   `topic_id` (Integer, ForeignKey("topics.id"), Indexed, Nullable=False)
    *   `score` (Integer, Default=0)
    *   `total` (Integer, Default=0): Total questions.
    *   `answers` (JSON, Nullable=True): Key-value pairing of question IDs and selected options.
    *   `weak_topics` (JSON, Nullable=True): Areas identified as needing review based on incorrect answers.
    *   `completed_at` (DateTime, Default=func.now())

#### 20. [QuestionAttempt](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/assessment.py#L48) (`question_attempts` table)
Defined in [assessment.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/assessment.py). Individual question reviews generated during student practice.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed, Nullable=False)
    *   `question_id` (Integer, ForeignKey("extracted_questions.id"), Indexed, Nullable=False)
    *   `selected_answer` (Text, Nullable=True)
    *   `is_correct` (Boolean, Nullable=True)
    *   `score` (Integer, Default=0)
    *   `weak_topics` (JSON, Nullable=True)
    *   `completed_at` (DateTime, Default=func.now())

#### 21. [Flashcard](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/flashcard.py#L12) (`flashcards` table)
Defined in [flashcard.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/flashcard.py). Definition of card contents.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `topic_id` (Integer, ForeignKey("topics.id"), Indexed, Nullable=False)
    *   `front_ar` (Text, Nullable=False): Question, definition term, or chemical formula.
    *   `back_ar` (Text, Nullable=False): Answer, translation, or definition.
    *   `created_by` (String(30), Default="system"): system, ai.
*   **Relationships:**
    *   `progress_records` $\to$ Many `FlashcardProgress`

#### 22. [FlashcardProgress](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/flashcard.py#L29) (`flashcard_progress` table)
Defined in [flashcard.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/flashcard.py). Keeps spaced repetition progress logs using the SM-2 algorithm.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed, Nullable=False)
    *   `flashcard_id` (Integer, ForeignKey("flashcards.id"), Indexed, Nullable=False)
    *   `mastered` (Boolean, Default=False)
    *   `review_count` (Integer, Default=0)
    *   `ease_factor` (Float, Default=2.5)
    *   `interval_days` (Integer, Default=0)
    *   `next_review_at` (Date, Nullable=True)
    *   `last_reviewed` (DateTime, Nullable=True)

#### 23. [StudyPlan](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/study_plan.py#L12) (`study_plans` table)
Defined in [study_plan.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/study_plan.py). Custom plan for exam dates.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed, Nullable=False)
    *   `exam_date` (Date, Nullable=True)
    *   `plan_json` (JSON, Nullable=True): Recommended day-by-day tasks.
    *   `status` (String(30), Default="active")

---

### Module F: Gamification & Progress Aggregation
These entities handle student progress visualization.

#### 24. [LessonProgress](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py#L67) (`lesson_progress` table)
Defined in [chemistry.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/chemistry.py). Progress logging for curriculum lessons.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed, Nullable=False)
    *   `lesson_id` (Integer, ForeignKey("lessons.id"), Indexed, Nullable=False)
    *   `status` (String(30), Default="not_started"): not_started, in_progress, completed.
    *   `completed_at` (DateTime, Nullable=True)

#### 25. [UserProgress](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/user_progress.py#L11) (`user_progress` table)
Defined in [user_progress.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/user_progress.py). Summarized topic metrics used to highlight user weak points and construct dashboards.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed, Nullable=False)
    *   `topic_id` (Integer, ForeignKey("topics.id"), Indexed, Nullable=False)
    *   `flashcards_mastered` (Integer, Default=0)
    *   `quizzes_completed` (Integer, Default=0)
    *   `best_quiz_score` (Float, Default=0.0): Maximum score percentage.
    *   `last_activity` (DateTime, Nullable=True)

#### 26. [Achievement](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/achievement.py#L12) (`achievements` table)
Defined in [achievement.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/models/achievement.py). Gamification system badges.
*   **Properties:**
    *   `id` (Integer, Primary Key)
    *   `user_id` (Integer, ForeignKey("users.id"), Indexed, Nullable=False)
    *   `name` (String(120), Nullable=False)
    *   `slug` (String(120), Nullable=True): e.g., "first_lesson_completed".
    *   `icon` (String(80), Nullable=True)
    *   `condition` (String(255), Nullable=True): Unlocking logic notes.
    *   `earned_at` (DateTime, Default=func.now())
