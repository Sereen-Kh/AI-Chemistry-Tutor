You are working on the EduMind Chemistry Tutor codebase.

We have a serious answer-quality problem in the Ask AI / RAG system.

Current behavior:
The app often answers incorrectly or says:
"لم أجد ذلك بوضوح في مقاطع الكتاب المتاحة"
even for simple chemistry questions.

Examples:

1. "ما هو رمز الماء؟"
   Expected:
   "الصيغة الكيميائية للماء هي H₂O."
   Current behavior:
   Sometimes not found or unrelated textbook answer.

2. "ما هو الماء؟"
   Expected:
   "الماء مركب كيميائي صيغته H₂O، ويتكوّن من ذرتي هيدروجين وذرة أكسجين."
   Current behavior:
   The system may retrieve acid chunks only because they contain "في الماء".

3. "ما هي الحموض؟"
   Expected:
   "الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺."
   The textbook contains this information.

4. "ما هي الأسس؟"
   Expected:
   "الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻."
   The textbook contains this information.

5. "ما لون ورقة عباد الشمس في المحاليل الحمضية؟"
   Expected:
   "تتلون ورقة عباد الشمس باللون الأحمر."

6. "ما لون ورقة عباد الشمس في المحاليل الأساسية؟"
   Expected:
   "تتلون ورقة عباد الشمس باللون الأزرق."

7. "Explain this differently with a simpler example."
   Expected:
   This should re-explain the previous answer using previous context.
   Current behavior:
   The backend treats it as a new RAG query and says not found.

Root cause:
The system currently behaves like:
question → RAG search → LLM answer

This is not enough.

Required behavior:
question
→ normalize Arabic
→ classify intent
→ detect entity
→ route the request
→ use chemistry dictionary/rules/book knowledge/RAG only when appropriate
→ validate final answer
→ return structured response with diagnostics

Important:
Do not fix this only by changing prompts.
Implement code-level routing, validation, diagnostics, and tests.

==================================================
PHASE 0 — PLAN FIRST
==================================================

Before editing files:

1. Inspect the repository.
2. Identify:
   - current Ask AI endpoint
   - request/response schema
   - RAG retriever
   - vector search code
   - chunk model/table
   - answer generation prompt
   - frontend Ask AI component
   - test structure
3. Produce an implementation plan.
4. List the exact files you will change.
5. Do not modify files until the plan is clear.

After the plan, implement phase by phase.

Constraints:

- Do not rewrite the whole backend.
- Preserve current API compatibility where possible.
- Add fields in a backward-compatible way.
- Do not remove existing RAG functionality.
- RAG should become one route among several, not the only route.
- Do not show internal Gemini/OCR warnings in student-facing answers.
- Add tests. The task is not complete until acceptance tests pass.

==================================================
PHASE 1 — ADD REQUEST FIELDS
==================================================

Update the Ask AI request schema to support:

{
"question": "...",
"conversation_id": "...",
"parent_message_id": "...",
"answer_scope": "auto | book_only | tutor_general",
"preferred_answer_type": "auto | text | image | audio | video | mixed",
"teaching_style": "real_life | simple | exam | visual | ...",
"source_types": ["textbook"]
}

Defaults:
answer_scope = "auto"
preferred_answer_type = "text"
source_types = ["textbook"]

Behavior:

- book_only:
  Only answer from textbook/book_knowledge/RAG.
  If exact answer is not found:
  "لم أجد ذلك بوضوح في مقاطع الكتاب المتاحة."

- auto:
  Use dictionary/rules for simple direct questions.
  Use textbook support if available.
  Use RAG when the question needs book context.
  If user explicitly says "من الكتاب", try book first.

- tutor_general:
  Answer like a chemistry teacher even if the answer is not in the textbook.
  Clearly label non-book-grounded answers.

==================================================
PHASE 2 — ADD STRUCTURED RESPONSE
==================================================

Update response schema to include:

{
"answer_type": "text | audio | image | video | mixed | clarification | not_found",
"route": "followup_rephrase | chemistry_rule | dictionary_first | book_first | book_knowledge | textbook_rag | general_tutor | not_found",
"grounding": "book | approved_dictionary | chemistry_rule | general_tutor | mixed | none",
"confidence": 0.0,
"blocks": [
{
"type": "text | equation | image | audio | video_script | source_page | clarification",
"content": "",
"url": null,
"page": null,
"metadata": {}
}
],
"sources": [
{
"book_id": "",
"page": null,
"chunk_id": "",
"chunk_type": "",
"score": 0.0
}
],
"diagnostics": {}
}

Do not expose diagnostics to normal students in the UI.
Diagnostics should be visible only in debug/admin mode.

==================================================
PHASE 3 — ADD ARABIC NORMALIZER
==================================================

Create module:

app/rag/arabic_normalizer.py

Implement normalize_arabic(text):

Normalize:

- remove diacritics
- remove tatweel
- normalize أ / إ / آ → ا
- normalize ى → ي
- normalize ؤ / ئ where useful
- normalize punctuation
- normalize Arabic/English digits
- normalize chemistry subscripts/superscripts:
  H₂O → H2O
  O₂ → O2
  H₂SO₄ → H2SO4
  H⁺ → H+
  OH⁻ → OH-

Return normalized text.

Examples:
"ما هو رمز H₂O؟" → "ما هو رمز H2O"
"ما هي الأسس؟" → "ما هي الاسس"

==================================================
PHASE 4 — ADD INTENT CLASSIFIER
==================================================

Create module:

app/rag/intent_classifier.py

Detect intents:

- definition_lookup
- formula_lookup
- property_lookup
- equation_lookup
- reaction_lookup
- lesson_navigation
- exercise_solving
- followup_rephrase
- general_explanation
- ambiguous

Examples:

"ما هو الماء؟"
→ definition_lookup, entity=الماء

"ما هو رمز الماء؟"
→ formula_lookup, entity=الماء

"ما صيغة حمض الكبريت؟"
→ formula_lookup, entity=حمض الكبريت

"ما هي الحموض؟"
→ definition_lookup, entity=الحموض

"ما هي الأسس؟"
→ definition_lookup, entity=الأسس

"ما لون ورقة عباد الشمس في المحلول الحمضي؟"
→ property_lookup, property=litmus_color, entity=acidic_solution

"هل يتفاعل النحاس مع حمض الكبريت الممدد؟"
→ reaction_lookup, entity=النحاس + حمض الكبريت الممدد

"اشرح بطريقة أبسط"
→ followup_rephrase

"Explain this differently with a simpler example"
→ followup_rephrase

==================================================
PHASE 5 — ADD ENTITY DETECTION AND SYNONYMS
==================================================

Create:

app/rag/data/chemistry_entities.json

Seed approved entries:

[
{
"id": "water",
"entity_ar": "الماء",
"aliases": ["الماء", "ماء", "H2O", "H₂O"],
"type": "compound",
"formula": "H₂O",
"answer_ar": "الماء مركب كيميائي صيغته H₂O، ويتكوّن من ذرتي هيدروجين وذرة أكسجين.",
"approved": true,
"grade_level": 9,
"confidence": 0.95
},
{
"id": "oxygen",
"entity_ar": "الأكسجين",
"aliases": ["الأكسجين", "الاكسجين", "أوكسجين", "اوكسجين", "O", "O2", "O₂"],
"type": "element",
"symbol": "O",
"formula": "O₂",
"answer_ar": "الأكسجين عنصر كيميائي رمزه O، ويوجد غالباً في الهواء على شكل غاز O₂.",
"approved": true,
"grade_level": 9,
"confidence": 0.95
},
{
"id": "hydrogen",
"entity_ar": "الهيدروجين",
"aliases": ["الهيدروجين", "الهدروجين", "H", "H2", "H₂"],
"type": "element",
"symbol": "H",
"formula": "H₂",
"answer_ar": "الهيدروجين عنصر كيميائي رمزه H، ويوجد غالباً على شكل غاز H₂.",
"approved": true,
"grade_level": 9,
"confidence": 0.95
},
{
"id": "acids",
"entity_ar": "الحموض",
"aliases": ["الحموض", "الأحماض", "الاحماض", "حمض", "المحاليل الحمضية", "H+"],
"type": "concept",
"answer_ar": "الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺.",
"approved": true,
"grade_level": 9,
"confidence": 0.95
},
{
"id": "bases",
"entity_ar": "الأسس",
"aliases": ["الأسس", "الاسس", "القواعد", "قاعدة", "المحاليل الأساسية", "المحاليل الاساسية", "OH-"],
"type": "concept",
"answer_ar": "الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻.",
"approved": true,
"grade_level": 9,
"confidence": 0.95
},
{
"id": "hydrochloric_acid",
"entity_ar": "حمض كلور الماء",
"aliases": ["حمض كلور الماء", "حمض الهيدروكلوريك", "HCl"],
"type": "compound",
"formula": "HCl",
"answer_ar": "صيغة حمض كلور الماء هي HCl.",
"approved": true,
"grade_level": 9,
"confidence": 0.95
},
{
"id": "sulfuric_acid",
"entity_ar": "حمض الكبريت",
"aliases": ["حمض الكبريت", "H2SO4", "H₂SO₄"],
"type": "compound",
"formula": "H₂SO₄",
"answer_ar": "صيغة حمض الكبريت هي H₂SO₄.",
"approved": true,
"grade_level": 9,
"confidence": 0.95
},
{
"id": "sodium_hydroxide",
"entity_ar": "هيدروكسيد الصوديوم",
"aliases": ["هيدروكسيد الصوديوم", "NaOH"],
"type": "compound",
"formula": "NaOH",
"answer_ar": "صيغة هيدروكسيد الصوديوم هي NaOH.",
"approved": true,
"grade_level": 9,
"confidence": 0.95
},
{
"id": "sodium_chloride",
"entity_ar": "كلوريد الصوديوم",
"aliases": ["كلوريد الصوديوم", "ملح الطعام", "NaCl"],
"type": "compound",
"formula": "NaCl",
"answer_ar": "صيغة كلوريد الصوديوم هي NaCl.",
"approved": true,
"grade_level": 9,
"confidence": 0.95
}
]

Only use approved=true entries for student-facing dictionary answers.

==================================================
PHASE 6 — ADD CHEMISTRY DICTIONARY LOOKUP
==================================================

Create:

app/rag/chemistry_dictionary.py

Behavior:

- For formula_lookup:
  If entity exists and has formula/symbol, answer directly.
- For definition_lookup:
  If entity exists and has answer_ar, answer directly.
- Return route=dictionary_first.
- Do not run broad RAG for simple direct facts unless textbook support is requested.

Examples:

Question:
"ما هو رمز الماء؟"
Expected:
"الصيغة الكيميائية للماء هي H₂O."

Question:
"ما هو الماء؟"
Expected:
"الماء مركب كيميائي صيغته H₂O، ويتكوّن من ذرتي هيدروجين وذرة أكسجين."

Question:
"ما هو الأكسجين؟"
Expected:
"الأكسجين عنصر كيميائي رمزه O، ويوجد غالباً في الهواء على شكل غاز O₂."

==================================================
PHASE 7 — ADD CHEMISTRY RULES
==================================================

Create:

app/rag/chemistry_rules.py

Implement deterministic rules.

Rule 1: litmus_color

If question asks about litmus paper color:

- acidic solution / acid / حمض / المحاليل الحمضية:
  "تتلون ورقة عباد الشمس باللون الأحمر في المحاليل الحمضية."

- basic solution / base / الأسس / القواعد / المحاليل الأساسية:
  "تتلون ورقة عباد الشمس باللون الأزرق في المحاليل الأساسية."

Rule 2: metal + dilute acid

Activity series:
K, Ba, Ca, Na, Mg, Al, Mn, Zn, Fe, Pb, H, Cu, Ag, Hg, Au

If metal is below H and acid is dilute/mamaddad/mukhaffaf:
Return:
"لا يحدث تفاعل بين [المعدن] والحمض الممدد في الظروف العادية، لأن [المعدن] أقل نشاطاً من الهيدروجين ولا يستطيع إزاحته من الحمض."

For copper + dilute sulfuric acid:
"لا يحدث تفاعل بين النحاس وحمض الكبريت الممدد في الظروف العادية، لأن النحاس أقل نشاطاً من الهيدروجين.
Cu + H₂SO₄ المخفف → لا تفاعل"

If question says concentrated hot sulfuric acid, do not use this dilute-acid rule.

==================================================
PHASE 8 — ADD BOOK KNOWLEDGE LAYER
==================================================

Create a book_knowledge lookup layer before raw RAG.

It can be JSON, DB table, or generated from chunks depending on current repo structure.

Required entries can be generated from textbook chunks or seeded:

- الحموض:
  statement:
  "الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺."
  source: acid definition page

- الأسس:
  statement:
  "الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻."
  source: base definition page

- acidic litmus:
  statement:
  "تتلون المحاليل الحمضية ورقة عباد الشمس باللون الأحمر."

- basic litmus:
  statement:
  "تتلون المحاليل الأساسية ورقة عباد الشمس باللون الأزرق."

- CaO + water:
  statement:
  "CaO + H₂O → Ca(OH)₂"

Use book_knowledge before broad vector retrieval when:

- intent is definition_lookup
- formula_lookup
- property_lookup
- known equation_lookup

==================================================
PHASE 9 — ADD CHUNK VALIDATION BEFORE USING RAG
==================================================

Create:

app/rag/chunk_validator.py

Do not accept irrelevant chunks just because they contain one keyword.

Rules:

For entity=الماء:

- Valid chunk must contain H2O/H₂O or a direct definition of water.
- Reject chunks where "الماء" appears only in phrases like:
  "في الماء"
  "انحلالها في الماء"
  "يتفاعل مع الماء"
  unless the question is about that reaction.

For entity=الحموض:

- Valid chunk must contain H+/H⁺ or "أيونات الهدروجين/الهيدروجين".

For entity=الأسس:

- Valid chunk must contain OH-/OH⁻ or "أيونات الهدروكسيد".

For litmus questions:

- Valid chunk must contain "ورقة عباد الشمس" and the expected color.

For reaction questions:

- Valid chunk must mention reactants or applicable reaction rule.
- Generic acid/base definitions are not valid for reaction questions.

Each retrieved chunk should include:
{
"valid_for_answer": true/false,
"rejection_reason": "..."
}

If no valid chunks remain:

- Do not answer from invalid context.
- Fall back according to answer_scope.

==================================================
PHASE 10 — ADD FINAL ANSWER VERIFICATION
==================================================

Before returning the final answer, verify that it satisfies the expected intent/entity.

Examples:

For "ما هو رمز الماء؟":

- answer must contain H₂O or H2O

For "ما هي الحموض؟":

- answer must contain H⁺/H+ or "أيونات الهدروجين/الهيدروجين"

For "ما هي الأسس؟":

- answer must contain OH⁻/OH- or "أيونات الهدروكسيد"

For litmus acid:

- answer must contain الأحمر

For litmus base:

- answer must contain الأزرق

If verification fails:

- Do not return the bad answer.
- Return a safe not_found or fallback dictionary/rule answer.
- Add diagnostics.verification_failed = true.

==================================================
PHASE 11 — FIX FOLLOW-UP QUESTIONS
==================================================

Implement conversation context.

Every answer should be stored with:

- message_id
- conversation_id
- original_question
- answer
- route
- selected_chunks
- sources
- diagnostics

If a new request has parent_message_id or is detected as followup_rephrase:

- Load previous message.
- Reuse previous question, answer, selected chunks, and sources.
- Do not run a new RAG search using only:
  "اشرح بطريقة أبسط"
  "لم أفهم"
  "Try differently"
  "Explain this differently"

Expected behavior:

Previous:
"ما هي الحموض؟"
Answer:
"الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺."

Follow-up:
"Explain this differently with a simpler example."

Expected:
"Bبساطة: الحمض مادة عندما تذوب في الماء تعطي H⁺. مثل حمض كلور الماء HCl، عندما يذوب في الماء يعطي H⁺."

Route:
followup_rephrase

==================================================
PHASE 12 — FIX FRONTEND PAYLOAD
==================================================

Inspect the Ask AI frontend.

The UI has answer type tabs:

- Video
- Image
- Audio
- Text

Make sure selecting a tab actually sends:

preferred_answer_type:

- video
- image
- audio
- text

Also send:

- answer_scope
- teaching_style
- conversation_id
- parent_message_id
- source_types

If audio is requested but TTS is not implemented:
Backend should return text answer plus diagnostics:
{
"audio_requested_but_tts_unavailable": true
}

Do not silently ignore the selected answer type.

==================================================
PHASE 13 — ADD DIAGNOSTICS
==================================================

Add diagnostics to every backend answer in debug/admin mode:

{
"original_question": "",
"normalized_question": "",
"resolved_question": "",
"is_followup": false,
"conversation_id": "",
"parent_message_id": "",
"answer_scope": "auto",
"preferred_answer_type": "text",
"intent": "",
"entity": "",
"route": "",
"retrieved_chunks": [
{
"chunk_id": "",
"page": null,
"score": 0.0,
"valid_for_answer": true,
"rejection_reason": null,
"preview": ""
}
],
"selected_context": [],
"confidence": 0.0,
"verification": {
"passed": true,
"reason": null
}
}

Do not display diagnostics to students by default.

==================================================
PHASE 14 — TESTS
==================================================

Add tests for these cases.
The task is not complete until they pass.

Test 1:
Question:
"ما هو رمز الماء؟"
answer_scope=auto
Expected:

- intent=formula_lookup
- route=dictionary_first
- answer contains H₂O or H2O
- "لم أجد" must not appear

Test 2:
Question:
"ما هو الماء؟"
Expected:

- route=dictionary_first
- answer contains H₂O or H2O
- answer contains "ذرتي هيدروجين" and "ذرة أكسجين"
- answer must not explain acids as the main answer

Test 3:
Question:
"ما هي الحموض؟"
Expected:

- route=dictionary_first or book_knowledge
- answer contains "أيونات الهدروجين" or "أيونات الهيدروجين"
- answer contains H⁺ or H+
- "لم أجد" must not appear

Test 4:
Question:
"ما هي الأسس؟"
Expected:

- route=dictionary_first or book_knowledge
- answer contains "أيونات الهدروكسيد"
- answer contains OH⁻ or OH-
- answer must not contain lesson objectives like "يتعرف"
- answer must not contain safety notes like "احتياطات"

Test 5:
Question:
"ما لون ورقة عباد الشمس في المحاليل الحمضية؟"
Expected:

- route=chemistry_rule or book_knowledge
- answer contains "الأحمر" or "الاحمر"
- answer is short and direct

Test 6:
Question:
"ما لون ورقة عباد الشمس في المحاليل الأساسية؟"
Expected:

- answer contains "الأزرق" or "الازرق"

Test 7:
Question:
"هل يتفاعل النحاس مع حمض الكبريت الممدد؟"
Expected:

- answer contains "لا يحدث تفاعل"
- answer contains "النحاس أقل نشاطاً من الهيدروجين"
- answer contains "Cu" and "H₂SO₄" if equations are supported

Test 8:
Question:
"ما هي معادلة تفاعل أكسيد الكالسيوم مع الماء؟"
Expected:

- answer contains "CaO"
- answer contains "H₂O" or "H2O"
- answer contains "Ca(OH)₂" or "Ca(OH)2"

Test 9:
Previous message:
"ما هي الحموض؟"

Follow-up:
"اشرح بطريقة أبسط"

Expected:

- route=followup_rephrase
- no new RAG search using only "اشرح بطريقة أبسط"
- answer re-explains previous answer
- "لم أجد" must not appear

Test 10:
Previous message:
"ما هي الحموض؟"

Follow-up:
"Explain this differently with a simpler example."

Expected:

- route=followup_rephrase
- answer uses previous context
- "لم أجد" must not appear

Test 11:
Question:
"ما هو رمز الماء؟"
preferred_answer_type=audio

Expected:

- backend receives preferred_answer_type=audio
- if TTS exists, response includes audio block
- if TTS does not exist, response includes text answer and diagnostics.audio_requested_but_tts_unavailable=true
- answer still contains H₂O

==================================================
PHASE 15 — FINAL REPORT
==================================================

After implementation, report:

1. Files changed.
2. New routing flow.
3. Request/response schema changes.
4. How dictionary/rules/book_knowledge/RAG are ordered.
5. How follow-up rephrase is handled.
6. How frontend answer type tabs are wired.
7. Diagnostics example for:
   "ما هو رمز الماء؟"
8. Test results for all acceptance tests.
9. Known limitations and next steps.
