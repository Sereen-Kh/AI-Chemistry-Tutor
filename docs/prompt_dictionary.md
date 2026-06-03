We need to implement a safer answer routing plan for EduMind Chemistry Tutor.

Current issue:
The system sends almost every question directly to textbook RAG. This causes wrong answers when the question wording changes. For example:
- "ما هو الماء؟" retrieves acid chunks because they contain "في الماء".
- "ما هي الأسس؟" may retrieve lesson objectives instead of the definition.
- "ما هو الأكسجين؟" may return not found even though a chemistry tutor should answer it.

Implement a routing system with answer_scope and an approved chemistry dictionary.

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

book_only:
- Only answer from textbook/book_knowledge/RAG.
- If exact answer is not found, return:
  "لم أجد ذلك بوضوح في مقاطع الكتاب المتاحة."
- Do not use dictionary or general tutor knowledge.

auto:
- Use intent/entity detection.
- For simple definition/formula/property questions, use approved dictionary/rules first.
- Then try to support the answer from the book.
- If the user explicitly says "من الكتاب", search the book first.
- If the book does not contain an exact answer but the approved dictionary does, answer with a clear label:
  "لم أجد ذلك بوضوح في مقاطع الكتاب المسترجعة، لكن من القاموس الكيميائي المعتمد: ..."

tutor_general:
- Use dictionary/rules/general chemistry even if not in the book.
- If not book-grounded, say so clearly.

==================================================
2. Add approved chemistry dictionary
==================================================

Create chemistry_entities.json or DB table.

Each entry must include:

{
  "id": "",
  "entity_ar": "",
  "aliases": [],
  "type": "element | compound | concept | property | reaction_rule",
  "answer_ar": "",
  "formula": null,
  "symbol": null,
  "approved": true,
  "grade_level": 9,
  "source_type": "teacher_dictionary",
  "confidence": 0.95
}

Use only entries where approved = true for student-facing answers.

Seed entries:
- الماء → H₂O
- الأكسجين → O / O₂
- الهيدروجين → H / H₂
- الحموض → تعطي H⁺
- الأسس → تعطي OH⁻
- حمض كلور الماء → HCl
- حمض الكبريت → H₂SO₄
- هيدروكسيد الصوديوم → NaOH
- كلوريد الصوديوم → NaCl
- ورقة عباد الشمس في الحمض → الأحمر
- ورقة عباد الشمس في الأساس → الأزرق

==================================================
3. Add intent/entity-based routing
==================================================

Do not always run textbook RAG first.

Routing rules:

A) If intent is formula_lookup, definition_lookup, property_lookup:
   - If answer_scope != book_only and approved dictionary/rule has exact entity:
       answer from dictionary/rule first.
       then optionally retrieve book support.
   - If question explicitly contains "من الكتاب":
       try book_knowledge/RAG first.
       if no exact book answer and answer_scope == auto:
           use approved dictionary with clear label.

B) If intent is lesson_navigation, exercise_solving, page_reference:
   - Use book_knowledge/RAG first.

C) If intent is reaction_lookup:
   - Use chemistry rules first if the rule is deterministic.
   - Then retrieve book support.

D) If no answer:
   - book_only → not_found
   - auto/tutor_general → dictionary/general tutor if safe and known

==================================================
4. Prevent false book matches
==================================================

For entity = "الماء":
Do not consider chunks valid just because they contain "في الماء" or "انحلالها في الماء".
A valid water answer must contain H2O/H₂O or a direct definition of water.

For entity = "الأسس":
Valid answer must contain OH-/OH⁻ or "أيونات الهدروكسيد".

For entity = "الحموض":
Valid answer must contain H+/H⁺ or "أيونات الهدروجين".

If retrieved chunks do not match validation criteria, treat book answer as not found.

==================================================
5. Response labeling
==================================================

Return route and grounding:

{
  "route": "dictionary_first | book_first | book_supported_dictionary | textbook_rag | not_found",
  "grounding": "book | approved_dictionary | general_tutor | mixed",
  "answer_scope": "auto",
  "confidence": 0.0,
  "blocks": [...],
  "sources": [...],
  "diagnostics": {...}
}

Do not show internal warnings to the student.

==================================================
6. Acceptance tests
==================================================

Test 1:
Question: "ما هو الماء؟"
answer_scope: auto
Expected:
- route = dictionary_first
- answer contains H₂O
- answer does not talk about acids.

Test 2:
Question: "ما هو الماء من الكتاب؟"
answer_scope: auto
Expected:
- book checked first.
- if exact book answer not found, answer from approved dictionary with label.

Test 3:
Question: "ما هو الماء من الكتاب؟"
answer_scope: book_only
Expected:
- if no exact book answer, say not found.
- do not use dictionary.

Test 4:
Question: "ما هي الأسس؟"
Expected:
- answer contains أيونات الهدروكسيد OH⁻.
- must not return lesson objectives.

Test 5:
Question: "ما هي الأسس من الكتاب؟"
Expected:
- book_knowledge/RAG first.
- answer from book if exact definition exists.

Test 6:
Question: "ما هو الأكسجين؟"
answer_scope: auto
Expected:
- answer from approved dictionary/general tutor.
- contains O and O₂.

Test 7:
Question: "ما هو الأكسجين؟"
answer_scope: book_only
Expected:
- not found if no exact book source.

Test 8:
Question: "ما لون ورقة عباد الشمس في المحاليل الحمضية؟"
Expected:
- answer contains الأحمر.
- direct short answer.