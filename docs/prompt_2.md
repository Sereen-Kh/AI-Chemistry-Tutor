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

Your task now is to improve the OCR/Vision/document extraction pipeline.

Important decision:
Do NOT use OCRArena.
Do NOT use separate OCR behavior for debugging and production.
Do NOT use the legacy google-generativeai SDK.

Use the new google-genai SDK as the only Gemini SDK.

Primary extraction method:

- Upload the PDF directly using the Gemini Files API.
- Let Gemini process the original PDF instead of rendering every page to PNG first.
- Use structured JSON output with response_mime_type="application/json" and a schema.
- Use rendered 300 DPI page images only as an internal fallback inside GeminiVisionProvider when direct PDF extraction fails for a page.

The goal is to extract the full Grade 9 Arabic Chemistry book:

- selectable text
- non-selectable/scanned text
- mixed text/image pages
- Arabic text
- diagrams
- tables
- chemical equations
- examples
- exercises/questions
- visible answer keys if present

Do not invent official answers.

============================================================
IMPLEMENTATION TASKS
============================================================

1. Replace SDK dependency

Update requirements.txt:

Remove:

- google-generativeai

Add:

- google-genai

Update imports from:

import google.generativeai as genai

to:

from google import genai
from google.genai import types

2. Update settings

Add or verify:

GEMINI_API_KEY
GEMINI_DOCUMENT_MODEL=gemini-3.5-flash
GEMINI_DOCUMENT_FALLBACK_MODEL=gemini-2.5-pro
PDF_IMAGE_FALLBACK_ENABLED=true
GEMINI_EMBEDDING_MODEL="text-embedding-004"
OCR_PROVIDER="gemini"
OCR_REQUIRED_FOR_VISION=true
ALLOW_PARTIAL_INGESTION=false
INGESTION_MODE="dry_run|production"
PDF_DIRECT_EXTRACTION_ENABLED=true
PDF_IMAGE_FALLBACK_ENABLED=true

3. Refactor Gemini provider

Create/update:

app/services/ocr/gemini_provider.py

Implement:

class GeminiVisionProvider:
async def extract_pdf_page(
self,
pdf_path: str,
page_number: int,
source_type: str,
neighboring_pages: list[int] | None = None,
) -> PageExtractionResult:
...

    async def extract_page_image_fallback(
        self,
        image_path: str,
        page_number: int,
        source_type: str,
    ) -> PageExtractionResult:
        ...

Behavior:

- Upload PDF using google-genai Files API.
- Cache uploaded file handle/URI per ingestion job.
- Extract page-specific content by asking Gemini for a specific page number.
- If direct PDF extraction fails or returns invalid/empty content, render that page to 300 DPI image and run Gemini on the image.
- Do not call OCRArena.
- Do not use legacy google-generativeai.

4. Use structured output

Define strict Pydantic models:

PageExtractionResult
ExtractedSection
ExtractedQuestion
ExtractedDiagram
ExtractedTable
ExtractedEquation

Schema:

{
"page_number": int,
"detected_language": "ar",
"sections": [
{
"heading": str | null,
"content": str,
"content_type": "text|table|diagram|equation|example|exercise|answer_key|mixed"
}
],
"questions": [
{
"question_text": str,
"question_type": "multiple_choice|true_false|short_answer|calculation|essay|unknown",
"options": list[str] | null,
"correct_answer": str | null,
"explanation": str | null,
"answer_source": "page|answer_key|unknown"
}
],
"diagrams": [
{
"title": str | null,
"description": str,
"labels": list[str],
"related_text": str | null
}
],
"tables": [
{
"title": str | null,
"markdown": str
}
],
"equations": [
{
"equation": str,
"description": str | null
}
],
"warnings": list[str]
}

Use response_mime_type="application/json".
Use response_schema or equivalent supported schema mode from google-genai.
Do not manually strip ```json fences.
Do not parse uncontrolled free-text as JSON unless fallback is absolutely required.

5. Update extraction prompt

Use this prompt for PDF page extraction:

You are extracting content from an Arabic Grade 9 Chemistry textbook PDF.

Extract ONLY page {page_number}.
Use neighboring pages only for context if provided, but do not mix their content into this page.

Return valid JSON matching the provided schema.

Rules:

- Preserve Arabic text exactly.
- Do not transliterate Arabic.
- Do not summarize.
- Extract all visible educational content from the target page.
- Extract headings, body text, side boxes, examples, exercises, tables, diagrams, labels, equations, and answer keys if visible.
- Preserve chemical notation: H₂O, CO₂, H₂SO₄, NaCl.
- Preserve reaction notation: 2H₂ + O₂ → 2H₂O.
- Extract tables as markdown.
- Describe diagrams clearly enough for retrieval-augmented generation.
- Extract all visible questions.
- If the official answer is visible, include it.
- If the answer is not visible, set correct_answer=null and answer_source="unknown".
- Do not invent answers.
- If text is unclear, add a warning.
- Return JSON only.

6. Keep page classification

Do not remove page classification.

Still classify pages as:

SELECTABLE_TEXT
NEEDS_VISION
MIXED_VISION

But change the processing rules:

SELECTABLE_TEXT:

- Extract local text using pdfplumber/PyMuPDF.
- If no important visual content exists, use local extraction only.
- If important visual content exists, call Gemini direct PDF extraction for the page.

NEEDS_VISION:

- Use Gemini direct PDF extraction.
- If direct PDF extraction fails, use rendered image fallback.

MIXED_VISION:

- Extract local text.
- Use Gemini direct PDF extraction.
- Merge local text + Gemini output.
- Deduplicate repeated paragraphs.
- Preserve diagrams/tables/equations/questions from Gemini.

7. Page cache format

For every page, save:

data/textbooks/{source_slug}/pages/page_001.json

Include:

{
"page_number": 1,
"page_type": "SELECTABLE_TEXT|NEEDS_VISION|MIXED_VISION",
"status": "completed_text_only|completed_with_pdf_vision|completed_with_image_fallback|failed|skipped_dry_run",
"extraction_methods": ["pdfplumber", "gemini_pdf", "gemini_image_fallback"],
"text_layer_content": "...",
"gemini_pdf_content": {...},
"gemini_image_fallback_content": {...},
"merged_content": "...",
"sections": [],
"questions": [],
"diagrams": [],
"tables": [],
"equations": [],
"warnings": [],
"errors": [],
"char_count": 0,
"completeness_score": 0.0
}

8. Improve chunking

Update app/services/chunking.py.

Current blind 650-character chunks are not sufficient.

New rules:

- chunk_size default: 900 Arabic characters
- chunk_overlap default: 180 Arabic characters
- chunk by section first
- keep each question with its options
- keep each table as one atomic chunk
- keep each equation with its explanation
- keep each diagram description with labels
- split only oversized text sections
- never split mid-equation
- never split mid-table
- never split question text from answer options

9. Store RAG chunks

Use PostgreSQL + pgvector.

Do not use Qdrant.

Use general table:

rag_chunks

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

10. Tests

Add tests for:

- google-genai SDK import works
- legacy google-generativeai is not used
- direct PDF extraction path is called for NEEDS_VISION
- MIXED_VISION uses local text + Gemini PDF extraction
- image fallback is used only when direct PDF extraction fails
- structured JSON output parses into PageExtractionResult
- no manual ```json fence stripping is required
- page cache includes extraction_methods and status
- section-aware chunking does not split tables
- section-aware chunking does not split equations
- question chunk keeps options together
- production mode fails if vision pages cannot be extracted
- dry-run mode reports skipped/incomplete vision pages clearly
- OCR-extracted chunks are retrievable through pgvector

Definition of done:

- google-generativeai removed.
- google-genai used.
- Direct PDF extraction implemented.
- Structured JSON schema extraction implemented.
- Rendered image fallback remains available inside Gemini provider.
- OCRArena not used anywhere.
- SELECTABLE_TEXT, NEEDS_VISION, MIXED_VISION are all handled.
- Mixed pages preserve both local text and Gemini visual extraction.
- Page cache exists for every processed page.
- Chunking is section-aware.
- Arabic text is preserved.
- Equations, tables, diagrams, and questions are not broken by chunking.
- compileall passes.
- FastAPI imports pass.
- ruff check passes.
