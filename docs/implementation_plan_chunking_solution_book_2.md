# Chemistry Solution Book Ingestion Pipeline — Implementation Plan

We are adding the Syria Grade 9 Chemistry Solution Book to the EduMind RAG ingestion pipeline. The goal is to extract, normalize, chunk (with sentence-aware limits), embed, and search solution chunks safely without contaminating textbook-only conceptual queries.

---

## User Review Required

> [!IMPORTANT]
> **Database Schema & Metadata**: Instead of introducing database schema migrations, we will store Solution Book identifiers (`document_id`, `document_type`, `related_document_id`, etc.) inside the existing `metadata_json` column of the `ContentSource` and `RagChunk` tables. This enables metadata filtering on both SQLite and PostgreSQL. We will map `document_type` to the indexed `source_type` column for maximum retrieval performance.

> [!WARNING]
> **RAG Routing for Exercise Solving**: We will modify the RAG routing priority. When the intent is `exercise_solving`, we will check the Solution Book RAG first. If an exact matched chunk is found with high confidence, we return it. If no high-confidence solution is retrieved, we fall back to the dynamic `math_solver` rule engine. This ensures we don't return standard textbook pages for calculation questions.

---

## Open Questions

There are no remaining open questions. The specifications are fully resolved.

---

## Proposed Changes

### 1. Data Folder Structure & Serving

#### [NEW] Directory: `data/textbooks/syria_grade_9/solution_book/`
We will move the uploaded `Chemistry_Solution_Book.pdf` to `data/textbooks/syria_grade_9/solution_book/Chemistry_Solution_Book.pdf`.

#### [MODIFY] [main.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/main.py)
Update the static media mount so that the media server serves files under `solution_book/` as well.

---

### 2. Page Extraction & OCR Requirement Detection

#### [MODIFY] [ingestion_pipeline.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ingestion_pipeline.py)
- Support `document_id`, `document_type`, and `related_document_id` in `run_full_ingestion()`.
- Add an OCR requirement detection function `detect_ocr_needed(text_content, visual_info)`.
- If the page is image/table/diagram-heavy, has broken characters, or is empty, mark `needs_ocr = True` and list reasons (e.g. `low_text_length`, `table_detected`, `formula_heavy_page`).
- Write structured page JSON matching the target schema to `pages/page_***.json`.
- Fail ingestion fast if `needs_ocr` is `True` but `ocr_provider` is set to `none`.

#### [MODIFY] [ocr/__init__.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/__init__.py)
- Support `ocr_provider = "none"` by returning a `NoneVisionProvider` that has `is_configured = False` and fails when called.

---

### 3. Formula and Text Normalization

#### [NEW] [arabic_normalizer.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ocr/normalization.py)
Create light Arabic and chemistry formula normalization helpers:
- Formula normalization: H₂O → H2O, OH⁻ → OH-, Ca(OH)₂ → Ca(OH)2, `C₁ × V₁ = C₂ × V₂` → `C1 × V1 = C2 × V2`.
- Arabic normalization: strip tatweel, normalize `أ/إ/آ` → `ا`, and `ى` → `ي` for search fields. Keep original Arabic text for display.

---

### 4. Solution Book Chunking (Sentence-Aware)

#### [MODIFY] [chunking.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chunking.py)
- Implement a sentence-aware text splitter `split_solution_book_text()` that splits only at sentence boundaries (`.`, `؟`, `!`, `؛`), paragraph boundaries, and table boundaries.
- Ensure it does not split inside chemical equations, formulas, calculation lines, or table rows.
- Classify solution chunks into semantic types: `exercise_question`, `exercise_solution`, `solution_step`, `final_answer`, `equation`, `table`, `explanation`, `diagram_solution`, `page_header`, `lesson_reference`.
- Format chunks as the specified solution book chunk JSON.

---

### 5. Chunk Linking to Textbook

#### [MODIFY] [ingestion_pipeline.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/ingestion_pipeline.py)
- After chunking, run a linking step `link_solution_to_textbook()`:
  - Query existing textbook chunks from `RagChunk`.
  - Match by lesson title, page number, exercise number, concept/entity, formulas, and text similarity.
  - Populate `linked_textbook_pages` and `linked_textbook_chunk_ids`.

---

### 6. Embeddings and Retrieval

#### [MODIFY] [embeddings.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/embeddings.py)
- Support embedding inputs containing prefix titles and metadata tags: `"Solution book | المحاليل المائية | السؤال الثالث | [formula] | [content]"`.

#### [MODIFY] [rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/rag.py)
- Support `document_id`, `document_type`, `related_document_id`, `content_type`, `lesson_no`, `source_pdf` in SQL filters.
- Support `source_types` filter (allowing combinations of `"textbook"` and `"solution_book"`).
- Add intent-based boosting for `exercise_solving` in `_hybrid_score()` (prefer solution book chunks over textbook chunks, boost exact formula and question matches).

#### [MODIFY] [semantic_rag.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/semantic_rag.py)
- Pass the custom filters and updated source types through the RAG pipeline.

---

### 7. RAG Integration & Image Mode

#### [MODIFY] [chat_service.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/app/services/chat_service.py)
- Update `source_router.py` to route queries containing `"حل"`, `"كتاب الحل"`, `"حل المسألة"` to `"solution_book"`.
- If the question is classified as `exercise_solving`:
  - Search RAG (with `"solution_book"` prioritized).
  - If a high-confidence solution exists, return it directly.
  - If not, call the local `math_solver` as a fallback.
- In image/source page rendering, if the chunk is from a solution book page, generate a `source_page` response block with `page: null`, `pdf_page: page_number`, and `image_url` matching `/media/books/chemistry_solution_book/pages/page_***.png`.

---

### 8. Quality Reporting & CLI Commands

#### [NEW] [ingest_document.py](file:///Users/sereenkh/Github-Projects/AI-Chemistry-Tutor/backend/scripts/ingest_document.py)
Create the new document ingestion command line tool supporting:
- `--pdf`, `--document-id`, `--document-type`, `--related-document-id`.
- Actions: `--extract-only`, `--chunk-only`, `--embed-only`.
- Force flags: `--force-reextract`, `--force-rechunk`, `--force-reembed`.
- `--ocr-provider`.
- Compiles the final Ingestion Quality Report, verifying failure criteria (e.g. check for mid-sentence chunk threshold, missing embeddings, page extraction errors).

---

## Verification Plan

### Automated Tests
We will add unit and integration tests inside `backend/tests/test_solution_book_ingestion.py` verifying:
1. Solution Book page extraction produces the target JSON structure.
2. OCR detection triggers appropriately for image-heavy and low-text pages.
3. Ingestion fails clearly if OCR is required but provider is `"none"`.
4. Sentence-aware chunking does not break sentences or chemical formulas mid-sentence.
5. Embeddings are generated successfully with the augmented text prefixes.
6. VectorDB filters (`document_type`, etc.) work as expected.
7. Semantic search retrieves solution chunks when filtering by `source_types = ["solution_book"]`.
8. Solution book RAG results are prioritized for exercise-solving queries.
9. Image/Source Page block formats and returns the correct solution book page URLs.

### Manual Verification
1. Run `python scripts/ingest_document.py --pdf data/textbooks/syria_grade_9/solution_book/Chemistry_Solution_Book.pdf --document-id chemistry_grade9_solution_book --document-type solution_book --related-document-id chemistry_grade9_textbook` and check console outputs and SQLite/PostgreSQL contents.
2. Query the Ask AI tutor via the API with `"حل السؤال الثالث صفحة 22"` and verify it returns solution book references and the correct source page blocks.
