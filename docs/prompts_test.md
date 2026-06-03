You are a Senior AI/ML Engineer and Backend Architect working on EduMind, an AI-powered Grade 9 Chemistry Tutor app.
You are working on the EduMind Chemistry Tutor backend.

Current problem:
The tutor depends too much on RAG over textbook chunks. Small changes in Arabic question wording cause wrong answers.

Examples:
1. User asks: "ما هو الماء؟"
Current behavior: retrieves acid chunks because they contain "في الماء".
Wrong answer: talks about acids.
Expected answer: "الماء مركب كيميائي صيغته H₂O، ويتكوّن من ذرتي هيدروجين وذرة أكسجين."

2. User asks: "ما هو الأكسجين؟"
Current behavior: says not found in the book.
Expected in auto/tutor mode: "الأكسجين عنصر كيميائي رمزه O، ويوجد غالباً في الهواء على شكل غاز O₂."

3. User asks: "ما هي الأسس؟"
Current behavior: returns lesson objectives or safety precautions.
Expected: "الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻."

4. User asks: "ما لون ورقة عباد الشمس في المحاليل الحمضية؟"
Expected: "تتلون ورقة عباد الشمس باللون الأحمر."

Root cause:
The pipeline currently does:
question → retrieve textbook chunks → answer

But it needs:
question → normalize Arabic → detect intent/entity → check chemistry knowledge/rules → use RAG only when needed → answer directly.

Implement a small chemistry knowledge layer before RAG.

==================================================
1. Add answer_scope
==================================================

Add request field:

answer_scope:
- auto
- book_only
- tutor_general

Default: auto.

Behavior:
- book_only:
  Only answer from textbook chunks. If not found, say:
  "لم أجد ذلك بوضوح في مقاطع الكتاب المتاحة."

- tutor_general:
  Answer as a chemistry tutor using internal/general chemistry knowledge. Do not require textbook source.

- auto:
  First check direct chemistry facts and rules.
  Then use textbook RAG for support if relevant.
  If not found in the book but known generally, answer and say:
  "لم أجد تعريفاً مباشراً في المقاطع المسترجعة من الكتاب."

==================================================
2. Add Arabic normalization
==================================================

Create arabic_normalizer.py.

Normalize:
- remove diacritics
- remove tatweel ـ
- normalize أ / إ / آ → ا
- normalize ى → ي
- normalize ة with alias handling
- normalize Arabic and English digits
- normalize punctuation
- normalize chemical subscripts:
  H₂O → H2O
  O₂ → O2
  H₂SO₄ → H2SO4
  OH⁻ → OH-
  H⁺ → H+

Return both:
- original_query
- normalized_query

==================================================
3. Add intent classifier
==================================================

Create intent_classifier.py.

Detect these intents:
- definition_lookup
- formula_lookup
- property_lookup
- equation_lookup
- reaction_lookup
- lesson_navigation
- exercise_solving
- general_explanation
- ambiguous

Rule examples:

"ما هو X؟", "ما هي X؟", "عرف X", "تعريف X"
=> definition_lookup

"ما رمز X؟", "ما صيغة X؟", "الرمز الكيميائي لـ X"
=> formula_lookup

"ما لون ...", "ماذا يحدث لورقة عباد الشمس ..."
=> property_lookup

"اكتب معادلة ...", "ما معادلة ...", "يتفاعل ... مع ..."
=> equation_lookup or reaction_lookup

"ماذا يحتوي الدرس الأول؟", "أهداف الدرس الثاني"
=> lesson_navigation

"احسب", "حل المسألة"
=> exercise_solving

Output schema:

{
  "intent": "definition_lookup",
  "entity": "الماء",
  "property": null,
  "answer_style": "direct",
  "confidence": 0.0
}

==================================================
4. Add entity detection and synonym mapping
==================================================

Create chemistry_entities.json or DB table.

Required entities:

الماء:
aliases: ["الماء", "ماء", "H2O", "H₂O"]
type: compound
formula: H₂O
definition_ar: "الماء مركب كيميائي يتكوّن من ذرتي هيدروجين وذرة أكسجين."
short_answer_ar: "الماء مركب كيميائي صيغته H₂O، ويتكوّن من ذرتي هيدروجين وذرة أكسجين."

الأكسجين:
aliases: ["الأكسجين", "الاكسجين", "اوكسجين", "أوكسجين", "O", "O2", "O₂"]
type: element
symbol: O
common_molecule: O₂
definition_ar: "الأكسجين عنصر كيميائي رمزه O، ويوجد غالباً في الهواء على شكل غاز O₂."
short_answer_ar: "الأكسجين عنصر كيميائي رمزه O، ويوجد غالباً في الهواء على شكل غاز O₂، وهو ضروري للتنفس ويساعد على الاحتراق."

الهيدروجين:
aliases: ["الهيدروجين", "الهدروجين", "H", "H2", "H₂"]
type: element
symbol: H
common_molecule: H₂
definition_ar: "الهيدروجين عنصر كيميائي رمزه H، ويوجد غالباً على شكل غاز H₂."

الحموض:
aliases: ["الحموض", "الأحماض", "احماض", "حمض", "المحاليل الحمضية", "H+"]
type: concept
definition_ar: "الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺."
key_ion: H⁺

الأسس:
aliases: ["الأسس", "الاسس", "القواعد", "قاعدة", "المحاليل الأساسية", "OH-"]
type: concept
definition_ar: "الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻."
key_ion: OH⁻

حمض كلور الماء:
aliases: ["حمض كلور الماء", "حمض الهيدروكلوريك", "HCl"]
formula: HCl

حمض الكبريت:
aliases: ["حمض الكبريت", "H2SO4", "H₂SO₄"]
formula: H₂SO₄

هيدروكسيد الصوديوم:
aliases: ["هيدروكسيد الصوديوم", "NaOH"]
formula: NaOH

كلوريد الصوديوم:
aliases: ["كلوريد الصوديوم", "ملح الطعام", "NaCl"]
formula: NaCl

==================================================
5. Add chemistry facts dictionary
==================================================

Create chemistry_facts.py.

This layer answers direct facts before RAG.

For definition_lookup:
- If entity exists in chemistry_entities:
  return entity.definition_ar or short_answer_ar.

For formula_lookup:
- If entity has formula/symbol:
  return direct formula answer.

Examples:

Question: "ما هو الماء؟"
Route: facts_dictionary
Answer: "الماء مركب كيميائي صيغته H₂O، ويتكوّن من ذرتي هيدروجين وذرة أكسجين."

Question: "ما رمز الماء؟"
Route: facts_dictionary
Answer: "الصيغة الكيميائية للماء هي H₂O."

Question: "ما هو الأكسجين؟"
Route: facts_dictionary
Answer: "الأكسجين عنصر كيميائي رمزه O، ويوجد غالباً في الهواء على شكل غاز O₂."

Question: "ما هي الأسس؟"
Route: facts_dictionary or textbook_knowledge
Answer: "الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻."

==================================================
6. Add chemistry rules layer
==================================================

Create chemistry_rules.py.

Implement small rule table.

Rule: litmus_color

If question asks about litmus color:
- acidic solution / acid / حمض / المحاليل الحمضية:
  answer: "تتلون ورقة عباد الشمس باللون الأحمر في المحاليل الحمضية."

- basic solution / base / الأسس / المحاليل الأساسية:
  answer: "تتلون ورقة عباد الشمس باللون الأزرق في المحاليل الأساسية."

Rule: metal + dilute acid

If user asks about a metal with dilute acid:
- metals above hydrogen in activity series react and release H₂
- metals below hydrogen do not react

Activity series include at least:
K, Ba, Ca, Na, Mg, Al, Mn, Zn, Fe, Pb, H, Cu, Ag, Hg, Au

Example:
Question:
"هل يتفاعل النحاس مع حمض الكبريت الممدد؟"

Answer:
"لا يحدث تفاعل بين النحاس وحمض الكبريت الممدد في الظروف العادية، لأن النحاس أقل نشاطاً من الهيدروجين ولا يستطيع إزاحته من الحمض.
Cu + H₂SO₄ المخفف → لا تفاعل"

Important:
If question says "حمض الكبريت المركز الساخن", then the reaction is different:
Cu + 2H₂SO₄(conc) → CuSO₄ + SO₂ + 2H₂O

==================================================
7. Add textbook-derived knowledge base
==================================================

During ingestion/chunking, extract structured knowledge from textbook chunks.

Create book_knowledge table or JSON.

Extract from chunk types:
- definition
- result
- learned_summary
- equation
- table
- activity
- solved_example

Each entry:

{
  "id": "",
  "book_id": "",
  "entity": "الأسس",
  "intent": "definition_lookup",
  "statement": "الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻.",
  "source_page": 125,
  "pdf_page": 19,
  "lesson_title": "المحاليل الأساسية",
  "chunk_id": "",
  "confidence": 0.95
}

Examples to extract:
- الحموض → مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺
- الأسس → مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻
- المحاليل الحمضية → تلون ورقة عباد الشمس بالأحمر
- المحاليل الأساسية → تلون ورقة عباد الشمس بالأزرق
- الماء → H₂O if present
- CaO + H₂O → Ca(OH)₂
- C1 × V1 = C2 × V2

Use book_knowledge before broad chunk retrieval when possible.

==================================================
8. Add routing logic
==================================================

Create answer_router.py.

Routing priority:

1. Normalize query.
2. Classify intent.
3. Detect entity/property.
4. If answer_scope != book_only:
   a. check chemistry_rules
   b. check chemistry_facts
5. Check book_knowledge for matching entity/intent.
6. If still no answer, use textbook RAG.
7. If still no answer:
   - book_only: return not_found
   - auto/tutor_general: answer generally if safe and known

Pseudo-code:

def answer_question(question, answer_scope="auto"):
    normalized = normalize_arabic(question)
    intent = classify_intent(normalized)
    entity = detect_entity(normalized)
    
    if answer_scope != "book_only":
        rule_answer = chemistry_rules.try_answer(intent, entity, normalized)
        if rule_answer:
            return direct_answer(rule_answer, route="chemistry_rules")
        
        fact_answer = chemistry_facts.try_answer(intent, entity)
        if fact_answer:
            source = try_get_textbook_support(entity, intent)
            return direct_answer(fact_answer, source=source, route="facts_dictionary")
    
    book_answer = book_knowledge.try_answer(entity, intent)
    if book_answer:
        return direct_answer(book_answer, route="book_knowledge")
    
    rag_answer = textbook_rag.answer(question, intent, entity)
    if rag_answer.confidence >= threshold:
        return rag_answer
    
    if answer_scope == "book_only":
        return not_found("لم أجد ذلك بوضوح في مقاطع الكتاب المتاحة.")
    
    return general_tutor_answer(question, intent, entity)

==================================================
9. Prevent generic keyword contamination
==================================================

If entity is "الماء":
- Do not retrieve chunks only because they contain "في الماء".
- Require H2O, "صيغة الماء", "الماء مركب", or direct water context.
- Penalize acid/base chunks where water is only solvent context.

If entity is "الأسس":
- Boost chunks containing "أيونات الهدروكسيد", "OH-", "الأسس: مواد".
- Penalize "الأهداف", "يتعرف", "يميز", "احتياطات".

If entity is "الحموض":
- Boost chunks containing "أيونات الهدروجين", "H+", "الحموض: مواد".
- Penalize generic safety/objective chunks.

==================================================
10. Direct answer first
==================================================

For these intents:
- definition_lookup
- formula_lookup
- property_lookup
- equation_lookup
- reaction_lookup

The answer must start with the direct answer.

Good:
"الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻."

Bad:
"إجابة مبنية على مقاطع الكتاب: يتعرّف الوظيفة الأساسية..."

Good:
"تتلون ورقة عباد الشمس باللون الأحمر في المحاليل الحمضية."

Bad:
"الحموض هي مواد تعطي H+ ..."

==================================================
11. Response schema
==================================================

Return structured answer blocks.

{
  "answer_type": "text | mixed | clarification | not_found",
  "route": "chemistry_rules | facts_dictionary | book_knowledge | textbook_rag | general_tutor",
  "confidence": 0.0,
  "blocks": [
    {
      "type": "text | equation | table | source_page | clarification",
      "content": "",
      "page": null,
      "image_url": null,
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

Do not show internal warnings like:
"تعذر استخدام Gemini حالياً..."
inside the student-facing answer.
Move such messages to diagnostics/admin mode only.

==================================================
12. Unknown-question logging
==================================================

Add unknown_questions table/log.

Whenever the system cannot answer confidently, log:

{
  "question": "",
  "normalized_query": "",
  "detected_intent": "",
  "detected_entity": "",
  "answer_scope": "",
  "rag_found": false,
  "route": "not_found",
  "needs_dictionary_entry": true,
  "created_at": ""
}

Purpose:
The dictionary should grow from real failed student questions.

Add an admin script:
python review_unknown_questions.py

It should list most frequent unknown entities/questions so we can add entries later.

==================================================
13. Seed dictionary size
==================================================

Do not try to build a huge chemistry dictionary now.

Start with 50–100 core entries:
- common elements: oxygen, hydrogen, carbon, sodium, chlorine, calcium, iron, copper, zinc
- common compounds: water, sodium chloride, hydrochloric acid, sulfuric acid, nitric acid, sodium hydroxide, potassium hydroxide, calcium hydroxide
- common concepts: acid, base, salt, solution, solute, solvent, molar concentration, mass concentration, dilution, chemical reaction
- common properties: litmus red/blue, acid/base ion, strong/weak acid/base
- common equations from the book

Make the structure expandable.

==================================================
14. Acceptance tests
==================================================

Add tests.

Test 1:
Question: "ما هو الماء؟"
answer_scope: auto
Expected:
- route = facts_dictionary
- answer contains "H₂O"
- answer contains "ذرتي هيدروجين وذرة أكسجين"
- answer must NOT mention acids as the main answer

Test 2:
Question: "ما هو رمز الماء؟"
Expected:
- route = facts_dictionary
- answer contains "H₂O"

Test 3:
Question: "ما هو الأكسجين؟"
answer_scope: auto
Expected:
- route = facts_dictionary or general_tutor
- answer contains "عنصر كيميائي"
- answer contains "O"
- answer contains "O₂"

Test 4:
Question: "ما هو الأكسجين؟"
answer_scope: book_only
Expected:
- if not found in textbook, answer says not found in textbook
- no fake textbook source

Test 5:
Question: "ما هي الحموض؟"
Expected:
- answer contains "أيونات الهدروجين"
- answer contains "H⁺"
- route = facts_dictionary or book_knowledge

Test 6:
Question: "ما هي الأسس؟"
Expected:
- answer contains "أيونات الهدروكسيد"
- answer contains "OH⁻"
- route = facts_dictionary or book_knowledge
- must NOT answer with lesson objectives

Test 7:
Question: "ما لون ورقة عباد الشمس في المحاليل الحمضية؟"
Expected:
- route = chemistry_rules or book_knowledge
- answer contains "الأحمر"
- short direct answer

Test 8:
Question: "ما لون ورقة عباد الشمس في المحاليل الأساسية؟"
Expected:
- answer contains "الأزرق"

Test 9:
Question: "هل يتفاعل النحاس مع حمض الكبريت الممدد؟"
Expected:
- route = chemistry_rules or book_knowledge
- answer contains "لا يحدث تفاعل"
- answer contains "النحاس أقل نشاطاً من الهيدروجين"
- answer contains "Cu + H₂SO₄ المخفف → لا تفاعل"

Test 10:
Question: "ما هي معادلة تفاعل أكسيد الكالسيوم مع الماء؟"
Expected:
- answer contains "CaO + H₂O → Ca(OH)₂"

==================================================
15. Final deliverable
==================================================

After implementation, provide:

1. Files changed.
2. Data model added.
3. How to add new dictionary entries.
4. How book_knowledge is generated from textbook chunks.
5. How unknown-question logging works.
6. Example outputs for all acceptance tests.
7. Any remaining limitations.