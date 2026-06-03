"""Focused tests for Arabic RAG ranking and local source fallback."""

from __future__ import annotations

import asyncio
from unittest import TestCase

from app.services.chat_service import (
    _classify_question,
    _dictionary_entry_for_question,
    _dictionary_response,
    _definition_entity_for_question,
    _direct_definition_response,
    _direct_property_response,
    _local_rag_answer,
    _not_found_response,
    _valid_book_chunks_for_dictionary_entry,
    ask_question,
)
from app.services.rag import RetrievedChunk, _hybrid_score, clean_query, lexical_relevance_score, rewrite_query


def chunk(chunk_id: int, page_number: int, content: str, score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        id=chunk_id,
        source_id=1,
        content=content,
        source="كتاب الكيمياء",
        source_type="textbook",
        content_type="text",
        page_number=page_number,
        chapter_id=None,
        lesson_id=None,
        topic_id=None,
        metadata_json=None,
        similarity_score=score,
    )


class ArabicRagRankingTests(TestCase):
    def test_acid_query_prefers_matching_textbook_chunk_over_weak_vector_score(self):
        query = "اشرح لي ما هي الحموض من الكتاب؟"
        acid_content = """
        :الحموض
        في صيغتها الأيونية H+ تحتوي الحموض على أيون الهدروجين.
        الحموض: موادّ تُعطي عند انحلالها في الماء أيَّونات الهدروجين.
        """
        unrelated_content = """
        أنواع الروابط المشتركة بين ذرات الكربون:
        رابطة مشتركة أحادية ورابطة مشتركة ثنائية ورابطة مشتركة ثلاثية.
        """

        self.assertGreater(lexical_relevance_score(query, acid_content), 0.7)
        self.assertEqual(lexical_relevance_score(query, unrelated_content), 0.0)
        self.assertGreater(
            _hybrid_score(query, acid_content, vector_score=0.12),
            _hybrid_score(query, unrelated_content, vector_score=0.6),
        )

    def test_local_fallback_extracts_answer_lines_instead_of_dumping_unrelated_chunks(self):
        answer = _local_rag_answer(
            "اشرح لي ما هي الحموض من الكتاب؟",
            [
                chunk(
                    13,
                    11,
                    """
                    :الحموض
                    في صيغتها الأيونية H+ تحتوي الحموض على أيون الهدروجين.
                    عدد الوظائف الحمضيَّة: هو عدد أيونات الهدروجين في الصّيغة الأيونية للحمض.
                    الحموض: موادّ تُعطي عند انحلالها في الماء أيَّونات الهدروجين.
                    """,
                ),
                chunk(
                    16,
                    13,
                    """
                    تتأيَّن الحموض القويَّة تأيّناً كلّيّاً في الماء.
                    تتأيَّن الحموض الضَّعيفة تأيّناً جزئيَّاً في الماء.
                    تلوّن المحاليل الحمضيَّة ورقة عباد الشَّمس باللَّون الأحمر.
                    """,
                ),
                chunk(
                    77,
                    77,
                    "صيغة الإيتن هي C2H4، والصيغة العامة للألكنات هي CnH2n.",
                    score=0.1,
                ),
            ],
            reason="تعذر استخدام Gemini حالياً، لذلك أعرض لك إجابة محلية من مصادر الكتاب.",
        )

        self.assertIn("من الكتاب", answer)
        self.assertIn("الحموض هي مواد", answer)
        self.assertIn("الحموض القوية تتأين كلياً", answer)
        self.assertIn("صفحة 11", answer)
        self.assertIn("13", answer)
        self.assertNotIn("صيغة الإيتن", answer)

    def test_bases_question_is_direct_definition_lookup(self):
        classification = _classify_question("ما هي الأسس؟")

        self.assertEqual(classification["intent"], "definition_lookup")
        self.assertEqual(classification["entity"], "الأسس")
        self.assertEqual(classification["normalized_entity"], "الاسس")
        self.assertEqual(classification["answer_style"], "direct")

    def test_base_definition_ranking_penalizes_objectives(self):
        query = rewrite_query(clean_query("ما هي الأسس؟"))
        definition_content = """
        الأسس: مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH-.
        تحتوي الأسس على أيون الهدروكسيد OH- في صيغتها الأيونية.
        """
        objectives_content = """
        الأهداف:
        - يتعرف الوظيفة الأساسية.
        - يميز بالتجربة بين الأسس القوية والأسس الضعيفة.
        - أثناء استعمال المحاليل الحمضية والقلوية يجب اتخاذ الاحتياطات.
        """

        definition_score = _hybrid_score(
            query,
            definition_content,
            vector_score=0.1,
            intent="definition_lookup",
            content_type="definition",
        )
        objectives_score = _hybrid_score(
            query,
            objectives_content,
            vector_score=0.8,
            intent="definition_lookup",
            content_type="objectives",
        )

        self.assertGreater(definition_score, objectives_score)

    def test_direct_base_definition_answer_is_short_and_focused(self):
        entity = _definition_entity_for_question("ما هي الأسس؟")
        self.assertIsNotNone(entity)
        assert entity is not None

        result = _direct_definition_response(
            entity=entity,
            chunks=[
                chunk(
                    18,
                    18,
                    "الأهداف: يتعرف الوظيفة الأساسية. يميز بالتجربة بين الأسس القوية والأسس الضعيفة. احتياطات.",
                    score=0.9,
                ),
                RetrievedChunk(
                    id=19,
                    source_id=1,
                    content="الأسس: مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH-.",
                    source="كتاب الكيمياء",
                    source_type="textbook",
                    content_type="definition",
                    page_number=19,
                    chapter_id=None,
                    lesson_id=None,
                    topic_id=None,
                    metadata_json=None,
                    similarity_score=0.72,
                ),
            ],
            preferred_answer_type="auto",
            diagnostics={"original_query": "ما هي الأسس؟"},
        )

        self.assertEqual(result["answer_type"], "text")
        self.assertGreater(result["confidence"], 0.75)
        self.assertIn("أيونات الهدروكسيد", result["answer"])
        self.assertIn("OH", result["answer"])
        self.assertNotIn("يتعرف الوظيفة الأساسية", result["answer"])
        self.assertNotIn("احتياطات", result["answer"])
        self.assertIn(19, result["page_numbers"])

    def test_direct_acid_definition_answer_has_no_objectives(self):
        entity = _definition_entity_for_question("ما هي الحموض؟")
        self.assertIsNotNone(entity)
        assert entity is not None

        result = _direct_definition_response(
            entity=entity,
            chunks=[
                RetrievedChunk(
                    id=11,
                    source_id=1,
                    content="الحموض: مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+.",
                    source="كتاب الكيمياء",
                    source_type="textbook",
                    content_type="definition",
                    page_number=11,
                    chapter_id=None,
                    lesson_id=None,
                    topic_id=None,
                    metadata_json=None,
                    similarity_score=0.82,
                ),
                chunk(10, 10, "الأهداف: يتعرف الحموض ويميز خصائصها.", score=0.7),
            ],
            preferred_answer_type="auto",
            diagnostics={"original_query": "ما هي الحموض؟"},
        )

        self.assertIn("أيونات الهدروجين H+", result["answer"])
        self.assertNotIn("الأهداف", result["answer"])
        self.assertIn(11, result["page_numbers"])

    def test_base_litmus_property_answer_is_blue_not_generic_definition(self):
        entity = _definition_entity_for_question("ما لون ورقة عباد الشمس في الأسس؟")
        self.assertIsNotNone(entity)
        assert entity is not None

        result = _direct_property_response(
            entity=entity,
            preferred_answer_type="auto",
            diagnostics={"original_query": "ما لون ورقة عباد الشمس في الأسس؟"},
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["diagnostics"]["intent"], "property_lookup")
        self.assertIn("الأزرق", result["answer"])
        self.assertNotIn("مواد تعطي عند انحلالها", result["answer"])

    def test_water_auto_uses_dictionary_first_without_acid_false_match(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما هو الماء؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(result["route"], "dictionary_first")
        self.assertEqual(result["grounding"], "approved_dictionary")
        self.assertIn("H₂O", result["answer"])
        self.assertNotIn("الحموض", result["answer"])

    def test_water_book_validation_rejects_in_water_acid_chunk(self):
        entry = _dictionary_entry_for_question("ما هو الماء؟", intent="definition_lookup")
        self.assertIsNotNone(entry)
        assert entry is not None

        valid, rejected = _valid_book_chunks_for_dictionary_entry(
            entry,
            [
                chunk(
                    11,
                    11,
                    "الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+.",
                    score=0.95,
                )
            ],
        )

        self.assertEqual(valid, [])
        self.assertEqual(len(rejected), 1)
        self.assertIn("exact evidence", rejected[0]["reason"])

    def test_water_from_book_only_not_found_does_not_use_dictionary(self):
        result = _not_found_response(
            question="ما هو الماء من الكتاب؟",
            answer_scope="book_only",
            preferred_answer_type="auto",
            diagnostics={"intent": "definition_lookup"},
            chunks=[
                chunk(
                    11,
                    11,
                    "الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+.",
                    score=0.95,
                )
            ],
        )

        self.assertEqual(result["route"], "not_found")
        self.assertEqual(result["answer_scope"], "book_only")
        self.assertNotIn("H₂O", result["answer"])
        self.assertIn("لم أجد ذلك بوضوح", result["answer"])

    def test_oxygen_auto_uses_approved_dictionary(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما هو الأكسجين؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(result["route"], "dictionary_first")
        self.assertIn("O", result["answer"])
        self.assertIn("O₂", result["answer"])

    def test_acid_litmus_dictionary_property_is_red(self):
        entry = _dictionary_entry_for_question(
            "ما لون ورقة عباد الشمس في المحاليل الحمضية؟",
            intent="property_lookup",
        )
        self.assertIsNotNone(entry)
        assert entry is not None

        result = _dictionary_response(
            entry=entry,
            question="ما لون ورقة عباد الشمس في المحاليل الحمضية؟",
            answer_scope="auto",
            preferred_answer_type="auto",
            route="dictionary_first",
            grounding="approved_dictionary",
            diagnostics={"intent": "property_lookup"},
        )

        self.assertEqual(result["route"], "dictionary_first")
        self.assertIn("الأحمر", result["answer"])
