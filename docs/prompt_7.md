We need to fix the EduMind Chemistry book ingestion pipeline.

Current issue:
Some cached page\_\*\*\*.json files were generated while Gemini OCR was not configured. They contain warnings/errors like:

"OCR provider 'gemini' is unavailable: GEMINI_API_KEY is not configured."
"Vision extraction skipped; text-layer fallback will be used when available."
"MIXED_VISION page requires OCR, but provider 'gemini' is not configured."
"NEEDS_VISION page requires OCR, but provider 'gemini' is not configured."

Because of this, the current chunks and embeddings are based on incomplete or broken extraction. Restarting the backend alone is not enough. We must re-extract the book and then re-chunk it.

Implement the following.

==================================================

1. # Verify Gemini configuration before ingestion

Before starting extraction, check that the required Gemini API key is configured.

The code currently appears to expect:

GEMINI_API_KEY

If the project uses the new google-genai SDK and expects GOOGLE_API_KEY instead, support both:

- GEMINI_API_KEY
- GOOGLE_API_KEY

Fail fast if no valid key is available and OCR/vision extraction is enabled.

Do not silently continue with incomplete OCR.

Expected behavior:
If a page is NEEDS_VISION or MIXED_VISION and Gemini is not configured, ingestion must fail with a clear error instead of generating degraded JSON.

Error message example:
"Vision OCR is required for this page, but GEMINI_API_KEY / GOOGLE_API_KEY is not configured. Aborting ingestion to avoid bad chunks."

================================================== 2. Add forced re-extraction and forced re-chunk flags
==================================================

Add CLI/API flags:

--force-reextract
--force-rechunk
--force-reembed

Behavior:

--force-reextract:

- Ignore existing page\_\*\*\*.json cache.
- Reprocess the PDF from the original Chemistry.pdf.
- Regenerate all page JSON files.

--force-rechunk:

- Delete old chunks for this book.
- Rebuild chunks from the newly extracted page JSON files.

--force-reembed:

- Delete old embeddings for this book.
- Recompute embeddings for the new chunks.

The recommended command should do all three:

python ingest.py --book Chemistry.pdf --force-reextract --force-rechunk --force-reembed

Adapt command name to the actual project structure.

================================================== 3. Invalidate old bad cached extraction
==================================================

Add cache validation logic.

Any page\_\*\*\*.json should be considered invalid if it contains:

- "OCR provider 'gemini' is unavailable"
- "Vision extraction skipped"
- "NEEDS_VISION page requires OCR"
- "MIXED_VISION page requires OCR"
- completeness_score == 0
- page_type in ["NEEDS_VISION", "MIXED_VISION"] and ocr_content is empty

If invalid:

- do not use it for chunking
- mark it as stale/bad
- force page re-extraction

Add a report like:

Bad cached pages found:

- page_003.json: NEEDS_VISION, OCR unavailable
- page_012.json: NEEDS_VISION, OCR unavailable
- page_020.json: NEEDS_VISION, OCR unavailable

================================================== 4. Re-extract the full Chemistry book
==================================================

Use this extraction priority:

1. Try PDF selectable text extraction.
2. If page has enough clean text and no important visuals, accept text layer.
3. If page is visual, table-heavy, formula-heavy, or low-quality:
   use Gemini vision OCR.
4. Store:
   - text_layer_content
   - ocr_content
   - merged_content
   - page image path
   - page_type
   - completeness_score
   - extraction_method
   - ocr_provider
   - warnings
   - errors

For pages with formulas/tables/diagrams, Gemini vision should extract:

- normal text
- equations
- tables
- figure captions
- activity questions
- page number

Do not let a visual page pass with empty extracted content.

================================================== 5. Fix formula reconstruction
==================================================

During extraction or post-processing, normalize common broken chemistry formulas.

Examples:

H O 2 -> H2O
H O N 3 -> HNO3
H O 2 3 C -> H2CO3
H P3 4 O -> H3PO4
H S2 4 O -> H2SO4
C V 1 1 # # = C V 2 2 -> C1 × V1 = C2 × V2
Ca (OH) 2 -> Ca(OH)2
H O 3 + -> H3O+

Also store a display version with subscripts:
H2O -> H₂O
H2SO4 -> H₂SO₄
Ca(OH)2 -> Ca(OH)₂

================================================== 6. Re-chunk only from clean extraction
==================================================

Do not chunk from bad page JSON.

Chunking should run only after all required pages have valid extraction.

Use pedagogical chunk types:

- lesson_header
- objectives
- keywords
- definition
- result
- activity
- equation
- example
- solved_example
- exercise
- table
- safety_note
- enrichment

Each chunk must contain metadata:

{
"book_id": "...",
"source_pdf": "Chemistry.pdf",
"unit": "...",
"lesson_no": 1,
"lesson_title": "المحاليل المائية",
"book_page": 108,
"pdf_page": 2,
"chunk_type": "objectives",
"title": "...",
"content": "...",
"entities": ["المحلول", "التركيز المولي"],
"formulas": ["C = n / V"],
"extraction_run_id": "...",
"extractor": "gemini",
"extractor_model": "...",
"completeness_score": 0.95
}

Do not create large raw page chunks only.

================================================== 7. Delete old chunks and embeddings
==================================================

Before inserting new chunks:

- delete old chunks for the Chemistry book
- delete old embeddings for those chunks
- delete old retrieval cache for that book
- optionally keep old extraction in an archive folder, but do not use it

Important:
Do not mix old chunks with new chunks.

================================================== 8. Restart backend and workers
==================================================

After code changes and after ingestion:

- restart backend API
- restart Celery/worker processes if used
- restart any embedding/retrieval service if separate

Reason:
The current running backend will not load the new code until restart.

Add a deployment note:
"Backend restart required after ingestion pipeline changes."

================================================== 9. Benchmark logic
==================================================

Current benchmark cannot fairly compare OCRArena vs improved Gemini because there is no cached OCRArena output yet.

Implement benchmark guard:

If OCRArena cache is missing:

- allow inspection of current Gemini extraction quality
- do not report a Gemini-vs-OCRArena comparison
- print:
  "OCRArena cache missing. Run OCRArena extraction first before comparison."

Add commands:

python ingest.py --book Chemistry.pdf --extractor gemini --force-reextract
python ingest.py --book Chemistry.pdf --extractor ocrarena --force-reextract
python benchmark_extraction.py --book Chemistry.pdf --compare gemini,ocrarena

Adapt command names to actual project.

================================================== 10. Add quality report after ingestion
==================================================

After ingestion, generate a report:

- total pages
- pages extracted by text layer only
- pages extracted by Gemini vision
- pages with warnings
- pages with errors
- pages with completeness_score < 0.75
- number of chunks
- number of equation chunks
- number of definition chunks
- number of table chunks

Fail ingestion if:

- any required page has errors
- any NEEDS_VISION page has no OCR
- any page has completeness_score == 0

================================================== 11. Acceptance tests after re-ingestion
==================================================

Run these QA tests after re-chunking and re-embedding:

1. "ما هو الرمز الكيميائي للماء؟"
   Expected:
   "الصيغة الكيميائية للماء هي H₂O."

2. "معادلة الماء؟"
   Expected:
   Ask clarification:
   "هل تقصد الصيغة الكيميائية للماء H₂O، أم معادلة تفكك الماء، أم معادلة تأينه؟"

3. "اعطني ماذا يحتوي الدرس الاول؟"
   Expected:
   Return lesson 1:
   "المحاليل المائية"
   and mention:

- المحلول المائي
- أنواع المحاليل المائية
- تحضير محلول
- التركيز الغرامي
- التركيز المولي
- الصفحات 108–115

4. "ما هو الحمض؟"
   Expected:
   "الحمض مادة تعطي عند انحلالها في الماء أيونات الهدروجين H+."

5. "ما هو الأساس؟"
   Expected:
   "الأساس مادة تعطي عند انحلالها في الماء أيونات الهدروكسيد OH-."

6. "ما لون ورقة عباد الشمس في الحمض؟"
   Expected:
   "تلوّن المحاليل الحمضية ورقة عباد الشمس باللون الأحمر."

7. "ما لون ورقة عباد الشمس في الأساس؟"
   Expected:
   "تلوّن المحاليل الأساسية ورقة عباد الشمس باللون الأزرق."

8. "اكتب معادلة تفاعل أكسيد الكالسيوم مع الماء"
   Expected:
   "CaO + H₂O → Ca(OH)₂"

================================================== 12. Final deliverable
==================================================

After implementation, provide:

1. Files changed.
2. Exact environment variables required.
3. Exact command to re-extract Chemistry.pdf.
4. Exact command to re-chunk and re-embed.
5. Exact command to restart backend/workers.
6. Ingestion quality report.
7. QA test results.
8. Whether OCRArena comparison is available or still blocked by missing cache.
