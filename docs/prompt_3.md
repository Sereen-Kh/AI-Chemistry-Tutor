You are a Senior AI/ML Engineer and Backend Architect working on EduMind, an AI-powered Grade 9 Chemistry Tutor app.

You specialize in:

- RAG systems
- OCR and document understanding
- Arabic educational content processing
- Chemistry textbook extraction
- FastAPI backend architecture
- PostgreSQL + pgvector
- SQLModel / async SQLAlchemy
- Celery background workers
- Redis caching
- AI tutoring systems
- adaptive quiz engines

Your task now is to fix and benchmark the document extraction pipeline.

Think like a production engineer, not a prototype builder.

Do not start by rewriting everything.
First inspect the current backend code and produce a short technical plan.
Then implement the extraction upgrade step by step.

============================================================
CONTEXT
============================================================

The current OCRArena result looks better than the current Gemini Vision API result.

Do not assume OCRArena is inherently better.

The likely reason is that the current Gemini implementation is weaker:

- it may use the legacy google-generativeai SDK
- it renders each PDF page to a 300 DPI PNG instead of using direct PDF/document input
- it prompts for JSON instead of using structured output mode
- it extracts page-by-page without neighboring context
- it chunks text blindly by character length
- it may lose tables, equations, Arabic glyphs, and PDF layout information

The goal is to make Gemini extraction comparable to OCRArena by using the best available Gemini document-processing path.

============================================================
HARD DECISIONS
============================================================

1. Do NOT use OCRArena as the production OCR/document extraction engine.

2. Do NOT add a separate debug OCR engine.

3. Debugging and production must use the same extraction code path.

4. Use OCRArena output only as a benchmark/reference if existing cached OCRArena results are available.

5. Do NOT use the legacy google-generativeai SDK.

6. Use the new google-genai SDK.

7. Primary extraction must use direct PDF upload/document processing.

8. Rendered 300 DPI page images are allowed only as fallback when direct PDF extraction fails for a page.

9. Use structured output mode:
   - response_mime_type="application/json"
   - response_schema or equivalent schema config
   - Pydantic models where supported

10. Do not manually strip ```json fences as the normal path.

11. Do not invent official answers.

12. Preserve Arabic text exactly.

13. Use PostgreSQL + pgvector for production RAG storage.

14. Do not use Qdrant for production.

============================================================
IMMEDIATE GOAL
============================================================

Create a fair benchmark and improved Gemini extraction pipeline.

The result should answer this question:

“Is OCRArena really better, or was our Gemini implementation weak?”

To answer this, implement:

A. Improved Gemini direct-PDF extraction
B. Structured schema output
C. Raw markdown + structured fields
D. Image fallback only when direct PDF extraction fails
E. Section-aware chunking
F. Benchmark against existing OCRArena output on the same pages

============================================================
FILES TO INSPECT FIRST
============================================================

Inspect these files if they exist:

- app/services/ocr/gemini_provider.py
- app/services/ocr/base.py
- app/services/pdf_processor.py
- app/services/ingestion_pipeline.py
- app/services/chunking.py
- app/services/embeddings.py
- app/core/config.py
- app/models/
- app/schemas/
- app/api/
- app/workers/
- requirements.txt
- docker-compose.yml
- migrations/
- data/textbooks/
- backend/scratch/
- any OCRArena extraction cache or page JSON files

After inspection, report:

1. Current Gemini SDK used
2. Current extraction path
3. Whether direct PDF upload exists
4. Whether structured output exists
5. Whether raw markdown is stored
6. Whether page cache exists
7. Whether OCRArena outputs are available for comparison
8. Current chunking behavior
9. Exact files to modify

Then implement.

============================================================
PHASE 1 — SDK MIGRATION
============================================================

Update dependencies.

Remove:

- google-generativeai

Add:

- google-genai

Update imports from:

import google.generativeai as genai

to:

from google import genai
from google.genai import types

Create a single Gemini client factory, for example:

app/services/gemini_client.py

Requirements:

- read API key from settings
- do not hardcode secrets
- support async usage where available
- centralize model names
- centralize retries/timeouts if already supported in project style

Settings to add or verify:

GEMINI_API_KEY
GEMINI_DOCUMENT_MODEL
GEMINI_DOCUMENT_FALLBACK_MODEL
GEMINI_EMBEDDING_MODEL="text-embedding-004"

PDF_DIRECT_EXTRACTION_ENABLED=true
PDF_IMAGE_FALLBACK_ENABLED=true

OCR_PROVIDER="gemini"
OCR_REQUIRED_FOR_VISION=true
ALLOW_PARTIAL_INGESTION=false
INGESTION_MODE="dry_run" | "production"

Important:
Do not hardcode one model name deeply inside services.
Use settings.

Suggested default:
GEMINI_DOCUMENT_MODEL should be the best available flash/pro document model configured in settings.
GEMINI_DOCUMENT_FALLBACK_MODEL should be a stronger model used only when extraction quality is poor.

============================================================
PHASE 2 — DATA CONTRACTS / SCHEMAS
============================================================

Create or update extraction schemas.

Suggested file:
app/schemas/extraction.py
or
app/services/ocr/schemas.py

Define strict Pydantic models:

PageExtractionResult
ExtractedSection
ExtractedQuestion
ExtractedDiagram
ExtractedTable
ExtractedEquation
ExtractionWarning
ExtractionQualityReport

PageExtractionResult must include:

- page_number: int
- detected_language: str
- raw_markdown: str
- sections: list[ExtractedSection]
- questions: list[ExtractedQuestion]
- diagrams: list[ExtractedDiagram]
- tables: list[ExtractedTable]
- equations: list[ExtractedEquation]
- warnings: list[str]
- completeness_score: float | None
- extraction_notes: str | None

ExtractedSection:

- heading: str | None
- content: str
- content_type: "text" | "table" | "diagram" | "equation" | "example" | "exercise" | "answer_key" | "mixed"

ExtractedQuestion:

- question_text: str
- question_type: "multiple_choice" | "true_false" | "short_answer" | "calculation" | "essay" | "unknown"
- options: list[str] | None
- correct_answer: str | None
- explanation: str | None
- answer_source: "page" | "answer_key" | "generated" | "unknown"

ExtractedDiagram:

- title: str | None
- description: str
- labels: list[str]
- related_text: str | None

ExtractedTable:

- title: str | None
- markdown: str

ExtractedEquation:

- equation: str
- description: str | None

Important:
raw_markdown is mandatory.
Do not store only structured fields.
The model may miss something in structured fields, but raw_markdown should keep the full extracted page content.

============================================================
PHASE 3 — GEMINI DIRECT PDF EXTRACTION
============================================================

Create/update:

app/services/ocr/gemini_provider.py

Implement:

class GeminiDocumentProvider:
async def prepare_document(self, pdf_path: str) -> UploadedDocumentRef:
"""
Upload the PDF using google-genai Files API.
Cache the uploaded file reference for the ingestion job.
"""

    async def extract_pdf_page(
        self,
        uploaded_pdf: UploadedDocumentRef,
        page_number: int,
        source_type: str,
        neighboring_pages: list[int] | None = None,
    ) -> PageExtractionResult:
        """
        Extract only one target page from the uploaded PDF.
        Use neighboring pages only as context.
        Return structured PageExtractionResult.
        """

    async def extract_page_image_fallback(
        self,
        image_path: str,
        page_number: int,
        source_type: str,
    ) -> PageExtractionResult:
        """
        Fallback only when direct PDF extraction fails or is too weak.
        """

Behavior:

- Upload the PDF once per ingestion job.
- Do not upload the PDF separately for every page.
- Extract one target page at a time.
- Optionally provide neighboring page numbers for context.
- Gemini must be instructed not to mix neighboring page content into target page output.
- Use structured output mode.
- Parse response into PageExtractionResult.
- If response.parsed exists, use it.
- Do not use manual JSON fence stripping in the normal path.

============================================================
PHASE 4 — EXTRACTION PROMPTS
============================================================

Use this prompt for direct PDF extraction:

You are extracting content from an Arabic Grade 9 Chemistry textbook PDF.

Target page: {page_number}

Extract ONLY the target page.
If neighboring page numbers are provided, use them only to understand context, headings, continuation, or references.
Do not include neighboring page content in the target page result.

Return valid JSON matching the provided schema.

Rules:

- Preserve Arabic text exactly.
- Do not transliterate Arabic.
- Do not summarize.
- Extract all visible educational content from the target page.
- Include a complete raw_markdown field containing the full extracted content of the target page.
- Extract headings, body text, side boxes, examples, exercises, tables, diagrams, labels, equations, and answer keys if visible.
- Preserve chemical notation such as H₂O, CO₂, H₂SO₄, NaCl.
- Preserve reaction notation such as 2H₂ + O₂ → 2H₂O.
- Extract tables as markdown.
- Describe diagrams clearly enough for retrieval-augmented generation.
- Extract all visible questions.
- Keep each question with its options.
- If an official answer is visible, include it.
- If the answer is not visible, set correct_answer=null and answer_source="unknown".
- Do not invent answers.
- If text is unclear, add a warning.
- Return JSON only.

For image fallback, use the same schema and rules.

============================================================
PHASE 5 — PAGE CLASSIFICATION AND ROUTING
============================================================

Keep the page classification system.

Page types:

- SELECTABLE_TEXT
- NEEDS_VISION
- MIXED_VISION

Processing rules:

SELECTABLE_TEXT:

- Extract local text using pdfplumber/PyMuPDF.
- Extract local tables if possible.
- If no important visual content exists, do not call Gemini.
- If important diagrams/tables/equations/images exist, call Gemini direct PDF extraction.

NEEDS_VISION:

- Use Gemini direct PDF extraction.
- If direct PDF extraction fails or is low quality, use rendered image fallback.

MIXED_VISION:

- Extract local text.
- Use Gemini direct PDF extraction.
- Merge local text with Gemini extraction.
- Deduplicate repeated paragraphs.
- Preserve all diagrams/tables/equations/questions from Gemini.

Important:

- MIXED_VISION must use Gemini.
- NEEDS_VISION must use Gemini.
- Production ingestion must not mark skipped vision pages as completed.

============================================================
PHASE 6 — QUALITY CHECK AND FALLBACK ROUTING
============================================================

Create a quality evaluator.

Suggested file:
app/services/ocr/quality.py

Implement:

evaluate_extraction_quality(result: PageExtractionResult) -> ExtractionQualityReport

Quality signals:

- raw_markdown length
- number of sections
- number of questions
- number of tables
- number of equations
- number of diagrams
- Arabic character ratio
- empty or near-empty output
- schema validity
- warnings count
- suspiciously low char_count
- page type expectation

Fallback rules:

- If direct PDF extraction fails structurally, retry with fallback model.
- If direct PDF extraction returns empty or very low content, retry with fallback model.
- If fallback model still fails, render page as 300 DPI image and use Gemini image fallback.
- If image fallback fails in production, mark page failed.
- If image fallback fails in dry_run, mark skipped_dry_run or failed_dry_run with warning.
- Do not silently mark failed vision pages as completed.

============================================================
PHASE 7 — PAGE CACHE
============================================================

For every processed page, save:

data/textbooks/{source_slug}/pages/page_001.json

Required fields:

{
"page_number": 1,
"page_type": "SELECTABLE_TEXT|NEEDS_VISION|MIXED_VISION",
"status": "completed_text_only|completed_with_pdf_extraction|completed_with_fallback_model|completed_with_image_fallback|failed|skipped_dry_run",
"extraction_methods": ["pdfplumber", "gemini_pdf", "gemini_pdf_fallback_model", "gemini_image_fallback"],
"text_layer_content": "...",
"gemini_pdf_content": {...},
"gemini_fallback_model_content": {...},
"gemini_image_fallback_content": {...},
"merged_content": "...",
"raw_markdown": "...",
"sections": [],
"questions": [],
"diagrams": [],
"tables": [],
"equations": [],
"warnings": [],
"errors": [],
"quality_report": {},
"char_count": 0,
"completeness_score": 0.0
}

============================================================
PHASE 8 — MERGE AND DEDUPLICATION
============================================================

For MIXED_VISION pages:

- Keep local text extraction.
- Keep Gemini direct PDF extraction.
- Merge them.
- Deduplicate repeated paragraphs.
- Do not delete diagrams.
- Do not delete tables.
- Do not delete equations.
- Do not delete questions.
- Prefer local text for long clean Arabic paragraphs if clearly better.
- Prefer Gemini for diagrams, tables, equations, visual labels, and question structure.
- Keep source attribution in metadata.

Implement simple deduplication first:

- normalize whitespace
- normalize Arabic punctuation spacing
- compare paragraph similarity
- remove obvious duplicates
- keep original page number and extraction method

============================================================
PHASE 9 — BENCHMARK AGAINST OCRArena OUTPUT
============================================================

If OCRArena cached outputs exist, use them only as benchmark data.

Do not call OCRArena live.
Do not require OCRArena cookies.
Do not require ngrok.
Do not add OCRArena to production path.

Create benchmark script:

scripts/benchmark_extraction.py

or admin/debug endpoint if appropriate:

POST /admin/ingestion/benchmark-extraction

Benchmark the same pages:

- one SELECTABLE_TEXT page
- one NEEDS_VISION page
- one MIXED_VISION page
- one table-heavy page
- one equation-heavy page
- one exercise/question page
- one diagram-heavy page

If exact pages are not known, select pages automatically based on classification and detected content.

Compare:
A. existing OCRArena cached output if available
B. old Gemini output if available
C. new Gemini direct PDF output
D. new Gemini fallback output if used

Scoring criteria:

- Arabic text completeness: 25%
- chemical equations accuracy: 20%
- tables: 15%
- diagrams and labels: 15%
- questions and options: 15%
- visible answers/answer keys: 5%
- valid structured output: 5%

Output report:

data/textbooks/{source_slug}/benchmarks/extraction_benchmark.json
data/textbooks/{source_slug}/benchmarks/extraction_benchmark.md

The report must include:

- per-page score
- per-method score
- missing content examples
- malformed equation examples
- table extraction comparison
- question extraction comparison
- recommendation: use Gemini direct PDF, retry with fallback model, or investigate prompt/model/preprocessing

Important:
If OCRArena still outperforms the improved Gemini pipeline, do not switch production automatically.
Report the gap and explain likely reason.

============================================================
PHASE 10 — SECTION-AWARE CHUNKING
============================================================

Update:

app/services/chunking.py

New rules:

- default chunk_size: 900 Arabic characters
- default chunk_overlap: 180 Arabic characters
- chunk by section first
- keep each table atomic
- keep each equation with its explanation
- keep each diagram description with its labels
- keep each question with its options
- split only oversized text sections
- never split mid-equation
- never split mid-table
- never split question text from options
- include page_number, content_type, source_type, extraction_method in metadata

Chunk sources:

- raw_markdown
- sections
- questions
- diagrams
- tables
- equations

Avoid duplicating everything:

- raw_markdown may be used as fallback
- structured items should become high-quality atomic chunks
- if raw_markdown duplicates structured chunks, mark it as summary/full_page chunk or skip according to configuration

============================================================
PHASE 11 — EMBEDDING AND STORAGE
============================================================

Use PostgreSQL + pgvector.

Use general table:
rag_chunks

Do not limit the system to textbook_chunks only.

Each chunk must include:

- source_id
- source_type
- page_number
- chapter_id nullable
- lesson_id nullable
- topic_id nullable
- content
- content_type
- extraction_method
- embedding VECTOR(768)
- metadata_json

Embedding:

- use Google text-embedding-004
- document chunks use task_type="retrieval_document"
- user queries use task_type="retrieval_query"

Do not use OpenAI embeddings.
Do not use VECTOR(1536).

============================================================
PHASE 12 — TESTS
============================================================

Add or update tests for:

1. google-genai SDK is used
2. legacy google-generativeai is not imported
3. direct PDF upload path is called
4. PDF is uploaded once per ingestion job
5. structured output parses into PageExtractionResult
6. raw_markdown is always present
7. manual JSON fence stripping is not used in normal path
8. NEEDS_VISION uses direct PDF extraction
9. MIXED_VISION uses local extraction + Gemini direct PDF extraction
10. image fallback is used only after direct PDF extraction fails
11. fallback model is used only when quality is low
12. dry_run records incomplete pages clearly
13. production mode fails or marks source incomplete when vision extraction fails
14. page cache contains status, methods, raw_markdown, structured fields, and quality_report
15. section-aware chunking does not split tables
16. section-aware chunking does not split equations
17. section-aware chunking keeps question options together
18. OCR/direct-PDF extracted chunks are stored in pgvector
19. Arabic query retrieves OCR/direct-PDF extracted content
20. benchmark report is generated if cached OCRArena output exists

============================================================
DEFINITION OF DONE
============================================================

- OCRArena is not used in production.
- OCRArena is not called live.
- Existing OCRArena output may be used only as benchmark/reference.
- google-generativeai is removed.
- google-genai is used.
- Direct PDF upload/document extraction is implemented.
- Structured JSON output is implemented.
- raw_markdown + structured fields are stored.
- Rendered image fallback exists only inside Gemini provider.
- Fallback model retry exists for low-quality extraction.
- SELECTABLE_TEXT, NEEDS_VISION, and MIXED_VISION are handled.
- Mixed pages preserve local text and Gemini extraction.
- Page cache JSON exists for every processed page.
- Section-aware chunking is implemented.
- Arabic text is preserved.
- Chemistry equations, tables, diagrams, and questions are not broken by chunking.
- Benchmark report can compare improved Gemini output to cached OCRArena output.
- PostgreSQL + pgvector remains production vector store.
- compileall passes.
- FastAPI imports pass.
- ruff check passes.
- Existing Swagger APIs still load.
