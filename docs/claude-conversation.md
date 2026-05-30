Continue RAG Ingestion From Claude Handoff
Summary
Continue the existing Gemini/OCRArena pipeline, per your choice, on Mac CPU/MPS.
Current state: Stage 1 is complete in data/textbooks/syria_grade_9/page_classification.json: 96 pages total, 65 SELECTABLE_TEXT, 24 NEEDS_VISION, 7 MIXED_VISION.
No per-page extraction cache exists yet, so the next real work is Stage 2: extract pages through Docling or OCRArena/Gemini, then rebuild chunks and seed Qdrant.
Important security note: claude converstation.md is untracked and contains pasted API material. Keep it uncommitted or sanitize it before any commit.
Interfaces And Config
Use existing scripts:
backend/scratch/extract_pages.py
backend/scratch/build_chunks.py
backend/scratch/seed_chunks.py
backend/scratch/test_rag.py
Required local env for Stage 2:
OCRARENA_COOKIE: full working browser/session cookie string.
OCRARENA_PUBLIC_BASE_URL: exact public URL that serves page_NNN.png, for example an ngrok forwarding URL, not just https://ngrok-free.app.
OCRARENA_MODEL_ID: optional; default already points to the Gemini 3 Flash model id in ocrarena_client.py.
Qdrant stays local by default at http://localhost:6333 with collection syria_grade_9_chemistry.
Final chunk payload shape remains: id, content, chapter, section, pages, page_types, content_types, extractors, language, char_count.
Implementation Steps
Prepare runtime:

Install backend dependencies if needed: pip install -r backend/requirements.txt.
Put OCRArena env vars in backend/.env or export them in the shell; do not commit them.
Create data/textbooks/syria_grade_9/pages/img.
Serve that folder locally with python3 -m http.server 8765, then expose it with ngrok and set OCRARENA_PUBLIC_BASE_URL to the ngrok HTTPS URL.
Dry-run extraction:

Run python3 backend/scratch/extract_pages.py --only 1,3,10 --force.
This covers one SELECTABLE_TEXT, one NEEDS_VISION, and one MIXED_VISION page.
Inspect generated pages/page_001.json, page_003.json, and page_010.json for readable Arabic text, diagram descriptions, tables/equations, content_types, and non-empty char_count.
Full extraction:

Run python3 backend/scratch/extract_pages.py.
Use the cache behavior to resume safely; rerun only failed pages with --only ... --force.
Acceptance target: 96 page_NNN.json files, with all 31 vision-routed pages successfully extracted.
Build and seed retrieval:

Run python3 backend/scratch/build_chunks.py; it backs up old chunks.json to chunks.v1.json.
Start Qdrant: docker compose up -d qdrant.
Run python3 backend/scratch/seed_chunks.py.
First bge-m3 run may download the model and be slow on Mac CPU/MPS.
Validate app retrieval:

Run python3 backend/scratch/test_rag.py.
Then smoke-test chat through the backend path, because chat_service.py already calls the Qdrant-backed rag_service.get_relevant_context().
Test Plan
Stage 2 dry-run succeeds for pages 1,3,10 with no empty content_md.
Full extraction count equals 96 cached page JSON files.
build_chunks.py produces more complete chunks than the old 100 text-only chunks and includes diagram/table/equation metadata where present.
seed_chunks.py creates/upserts the Qdrant collection without duplicate points.
test_rag.py --query "ما هو الجدول الدوري؟" --limit 5 returns relevant chunks with page references.
A chat question that requires textbook grounding receives context-backed Arabic output.
Assumptions
We are intentionally continuing with the current Gemini/OCRArena path, even though it is not fully open-source and may not remain free.
No local VLM replacement is planned in this continuation pass.
Secrets stay only in ignored env files or shell environment.
page_classification.json is useful output and can be kept; claude converstation.md should not be committed unless sanitized.
