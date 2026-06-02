You are a Senior AI/ML Engineer and Backend Architect working on EduMind,
an AI-powered Grade 9 Chemistry Tutor app.

You are working on the EduMind Chemistry Tutor RAG system.

Current problem:
The answer quality is poor even though the Chemistry book and page chunks are available as sources. The system often retrieves irrelevant pages and gives answers that do not directly answer the student question.

Examples of wrong behavior:

1. User asks: "ما هو الرمز الكيميائي للماء؟"
   Expected answer: "الصيغة الكيميائية للماء هي H₂O."
   Current behavior: retrieves unrelated pages about chemical reactions or general water mentions.

2. User asks: "معادلة الماء؟"
   Expected behavior: detect ambiguity and ask:
   "هل تقصد الصيغة الكيميائية للماء H₂O، أم معادلة تفكك الماء، أم معادلة تأينه؟"
   Current behavior: answers randomly from retrieved context.

3. User asks: "اعطني ماذا يحتوي الدرس الاول؟"
   Expected answer: show lesson 1 content/objectives from the book structure.
   Current behavior: semantic search retrieves unrelated pages.

Main goal:
Improve the RAG pipeline so that the Chemistry Tutor answers Arabic student questions accurately, using the book when relevant, and refusing/clarifying when retrieval confidence is low.

Implement the following improvements.

==================================================

1. # Add Arabic normalization

Create a reusable Arabic normalization function used before:

- embedding search
- BM25 search
- intent classification
- keyword matching

Normalize:

- remove tatweel ـ
- normalize أ / إ / آ → ا
- normalize ى → ي
- optionally normalize ة with both variants where useful
- remove excessive diacritics
- normalize Arabic and English digits
- normalize chemical subscripts:
  H₂O → H2O
  H₂SO₄ → H2SO4
  CO₂ → CO2

Also preserve the original query for display.

Example:
"ما هو الرمز الكيميائي للماء؟" should produce normalized tokens including:
["رمز", "كيميائي", "ماء", "الماء"]

# ================================================== 2. Add query intent classification

Before retrieval, classify the user question into one of these intents:

- formula_lookup
  Examples:
  "ما هو الرمز الكيميائي للماء؟"
  "صيغة الماء"
  "رمز حمض كلور الماء"

- lesson_navigation
  Examples:
  "ماذا يحتوي الدرس الاول؟"
  "اعطني اهداف الدرس الثاني"
  "ملخص الدرس 1"

- definition_lookup
  Examples:
  "ما هو الحمض؟"
  "عرف الأساس"
  "ما معنى التركيز المولي؟"

- equation_lookup
  Examples:
  "اكتب معادلة تأين حمض كلور الماء"
  "معادلة تفكك الماء"
  "معادلة تفاعل أكسيد الكالسيوم مع الماء"

- exercise_solving
  Examples:
  "حل المسألة"
  "احسب التركيز المولي"
  "كم كتلة حمض الخل"

- general_explanation
  Examples:
  "اشرح لي الحموض"
  "لماذا الماء المقطر لا ينقل التيار؟"

- ambiguous
  Example:
  "معادلة الماء؟"

Use a simple rule-based classifier first. Do not rely only on the LLM.
For ambiguous short questions, ask a clarification instead of retrieving random pages.

# ================================================== 3. Create a lesson index

Do not use vector search for lesson navigation questions.

Create a structured lesson index during ingestion or as a static generated JSON.

Example structure:

{
"unit": "الكيمياء اللاعضوية",
"lessons": [
{
"lesson_no": 1,
"title": "المحاليل المائية",
"pdf_pages": [2,3,4,5,6,7,8,9],
"book_pages": [108,109,110,111,112,113,114,115],
"objectives": [
"يتعرّف المحلول المائي",
"يميّز أنواع المحاليل المائية: متجانسة وغير متجانسة",
"يقوم بإجراء تجربة تحضير محلول",
"يتعرّف التركيز الغرامي",
"يتعرّف التركيز المولي"
],
"keywords": [
"المحلول",
"المادة المذيبة",
"المادة المذابة",
"التركيز الغرامي",
"التركيز المولي"
]
},
{
"lesson_no": 2,
"title": "المحاليل الحمضية"
},
{
"lesson_no": 3,
"title": "المحاليل الأساسية"
},
{
"lesson_no": 4,
"title": "أنواع التفاعلات الكيميائية"
},
{
"lesson_no": 5,
"title": "الأملاح"
}
]
}

When the intent is lesson_navigation:

- map "الأول" / "اول" / "1" → lesson_no 1
- return lesson title, objectives, key topics, and source pages
- do not perform normal vector search unless needed for details

Expected answer for:
"اعطني ماذا يحتوي الدرس الاول؟"

Should be:
"الدرس الأول هو: المحاليل المائية. يحتوي على: تعريف المحلول المائي، أنواع المحاليل المائية، تجربة تحضير محلول، التركيز الغرامي، التركيز المولي. الصفحات: 108–115."

# ================================================== 4. Create a chemistry facts and formula dictionary

Add a small but expandable dictionary for direct chemistry facts.

Example:

{
"الماء": {
"formula": "H₂O",
"aliases": ["ماء", "الماء", "water", "H2O"]
},
"حمض كلور الماء": {
"formula": "HCl",
"aliases": ["حمض كلور الماء", "حمض الهيدروكلوريك", "HCl"]
},
"حمض الكبريت": {
"formula": "H₂SO₄",
"aliases": ["حمض الكبريت", "H2SO4"]
},
"حمض الآزوت": {
"formula": "HNO₃",
"aliases": ["حمض الآزوت", "حمض الازوت", "HNO3"]
},
"حمض الخل": {
"formula": "CH₃COOH",
"aliases": ["حمض الخل", "CH3COOH"]
},
"هيدروكسيد الصوديوم": {
"formula": "NaOH",
"aliases": ["هيدروكسيد الصوديوم", "NaOH"]
},
"هيدروكسيد البوتاسيوم": {
"formula": "KOH",
"aliases": ["هيدروكسيد البوتاسيوم", "KOH"]
},
"كلوريد الصوديوم": {
"formula": "NaCl",
"aliases": ["كلوريد الصوديوم", "ملح الطعام", "NaCl"]
}
}

For formula_lookup:

- check this dictionary first
- answer directly
- optionally retrieve a supporting book page only if needed
- do not run broad semantic search on generic words like "الماء"

Expected answer:
User: "ما هو الرمز الكيميائي للماء؟"
Assistant: "الصيغة الكيميائية للماء هي: H₂O."

# ================================================== 5. Improve chunking strategy

Do not chunk only by fixed character length.

Use pedagogical chunks:

- lesson
- section
- activity
- definition
- result
- example
- exercise
- equation
- table

Each chunk should have metadata:

{
"book_id": "...",
"unit": "الكيمياء اللاعضوية",
"lesson_no": 2,
"lesson_title": "المحاليل الحمضية",
"book_page": 117,
"pdf_page": 11,
"chunk_type": "definition",
"title": "تعريف الحموض",
"content": "...",
"entities": ["الحموض", "H+", "أيون الهدروجين"]
}

Special handling:

- definitions should be small and precise
- equations should be stored as standalone searchable chunks
- tables should be reconstructed into clean markdown or JSON
- examples/exercises should keep the full question + solution together

Bad:
One long page chunk with broken formula text.

Good:
Separate chunk:
{
"chunk_type": "definition",
"content": "الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+."
}

# ================================================== 6. Fix OCR / vision fallback

Some pages are marked NEEDS_VISION or MIXED_VISION and currently OCR is unavailable.
This causes missing source content.

Implement:

- PDF text extraction first
- if page has low text completeness or page_type = NEEDS_VISION / MIXED_VISION:
  use OCR or vision extraction
- store both:
  - raw page image
  - extracted text
  - structured content

Add completeness_score.
If completeness_score < threshold, do not trust that page as fully indexed.

Also fix chemical formula reconstruction where possible:
Examples:

- "H O N 3" → "HNO3"
- "H O 2 3 C" → "H2CO3"
- "H P3 4 O" → "H3PO4"
- "C V 1 1 # # = C V 2 2" → "C1 × V1 = C2 × V2"

# ================================================== 7. Use hybrid retrieval

Do not use vector search alone.

Implement retrieval pipeline:

1. Normalize query
2. Detect intent
3. Query rewrite
4. Retrieve using:
   - BM25 / full text search
   - vector search
   - metadata filters
5. Merge results
6. Rerank
7. Apply confidence gate

For PostgreSQL:

- use pgvector for semantic retrieval
- use PostgreSQL full-text search or a BM25 implementation for lexical retrieval
- combine scores with weighted fusion

Example scoring:
final*score =
0.45 * vector*score +
0.35 * bm25*score +
0.15 * metadata*score +
0.05 * exact_entity_match

Metadata boost examples:

- matching lesson title
- matching chunk_type
- exact formula/entity match
- matching book_page requested by the question

# ================================================== 8. Add reranking

After initial retrieval, rerank top 20 chunks.

Use either:

- cross-encoder reranker
- LLM-based reranker with strict JSON output
- simple heuristic fallback if no reranker is available

Rerank based on:

- Does this chunk directly answer the question?
- Does it contain the requested entity?
- Does it contain the requested formula/equation/definition?
- Is it from the correct lesson/page?
- Is it too generic?

For:
"ما هو الرمز الكيميائي للماء؟"

A chunk mentioning "الماء" many times should not rank high unless it contains "H2O" or a direct formula context.

# ================================================== 9. Add confidence gate

Do not answer from weak retrieval.

Rules:

- If top reranker score < 0.55:
  - do not produce a source-grounded answer
  - either ask clarification or say that the source was not clear
- If intent is formula_lookup and dictionary has answer:
  - answer directly even if source retrieval is weak
- If query is ambiguous:
  - ask clarification
- If sources disagree:
  - explain uncertainty

Example:
"لم أجد في المقاطع المسترجعة صفحة واضحة تجيب عن السؤال مباشرة. لكن كيميائياً، الصيغة المعروفة للماء هي H₂O."

# ================================================== 10. Separate book-grounded answer from tutor answer

Implement two modes:

A. Book-grounded mode:

- Only answer using retrieved chunks.
- Cite source pages.
- Do not add external facts.

B. Tutor mode:

- Can explain using general chemistry.
- Must clearly label what comes from the book and what is general explanation.

Example:
"من الكتاب: الحموض تعطي عند انحلالها في الماء أيونات الهدروجين H+.
شرح مبسط: لذلك تسمى محاليل حمضية وتلوّن ورقة عباد الشمس بالأحمر."

# ================================================== 11. Improve answer prompt

Replace the current answer prompt with this behavior:

You are an Arabic chemistry tutor for school students.

Rules:

1. Answer the student's question directly first.
2. Use the retrieved book sources only if they actually support the answer.
3. Do not cite unrelated pages.
4. If the question is ambiguous, ask one short clarification question.
5. If the question asks for a formula or symbol, give the formula immediately.
6. If the retrieved sources are weak, say this clearly.
7. Keep the answer short, clear, and suitable for a student.
8. Do not list many pages unless they are relevant.
9. Prefer Arabic terms used in the book.
10. For chemical formulas, format them cleanly:
    H₂O, HCl, H₂SO₄, NaOH, Ca(OH)₂
11. If the answer is based on the book, include:
    - page number
    - chunk type if available
    - confidence score

# ================================================== 12. Expected outputs / acceptance tests

Add tests for the following questions.

Test 1:
Input:
"ما هو الرمز الكيميائي للماء؟"

Expected:
"الصيغة الكيميائية للماء هي H₂O."
No unrelated pages.

Test 2:
Input:
"معادلة الماء؟"

Expected:
Clarification:
"هل تقصد الصيغة الكيميائية للماء H₂O، أم معادلة تفكك الماء، أم معادلة تأينه؟"

Test 3:
Input:
"اعطني ماذا يحتوي الدرس الاول؟"

Expected:
Mention:

- الدرس الأول: المحاليل المائية
- المحلول المائي
- أنواع المحاليل المائية
- تحضير محلول
- التركيز الغرامي
- التركيز المولي
- الصفحات 108–115

Test 4:
Input:
"ما هو الحمض؟"

Expected:
Use book definition:
"الحمض هو مادة تعطي عند انحلالها في الماء أيونات الهدروجين H+."

Test 5:
Input:
"ما هو الأساس؟"

Expected:
Use book definition:
"الأساس هو مادة تعطي عند انحلالها في الماء أيونات الهدروكسيد OH-."

Test 6:
Input:
"ما لون ورقة عباد الشمس في الحمض؟"

Expected:
"تلوّن المحاليل الحمضية ورقة عباد الشمس باللون الأحمر."

Test 7:
Input:
"ما لون ورقة عباد الشمس في الأساس؟"

Expected:
"تلوّن المحاليل الأساسية ورقة عباد الشمس باللون الأزرق."

Test 8:
Input:
"اكتب معادلة تفاعل أكسيد الكالسيوم مع الماء"

Expected:
"CaO + H₂O → Ca(OH)₂"

# ================================================== 13. Implementation constraints

- Do not rewrite the whole backend unless necessary.
- Preserve current APIs where possible.
- Add migrations only if metadata/schema changes require them.
- Keep the system modular:
  - arabic_normalizer.py
  - intent_classifier.py
  - chemistry_facts.py
  - lesson_index.py
  - hybrid_retriever.py
  - reranker.py
  - confidence_gate.py
- Add unit tests.
- Add integration tests for the QA endpoint.
- Log retrieval diagnostics:
  - normalized_query
  - intent
  - rewritten_query
  - selected route
  - retrieved chunk IDs
  - scores
  - final confidence
  - whether answer is book-grounded or tutor-mode

# ================================================== 14. Final deliverable

After implementation, provide:

1. Summary of changed files.
2. Explanation of the new retrieval flow.
3. Example output for the 8 acceptance tests.
4. Any remaining limitations.
5. Clear instructions for running ingestion again on the Chemistry book.
