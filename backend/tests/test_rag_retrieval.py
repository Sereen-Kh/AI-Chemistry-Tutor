"""Focused tests for Arabic RAG ranking and local source fallback."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from app.core.config import settings
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
from app.services.rag import (
    RetrievedChunk,
    _hybrid_score,
    _retrieval_eligibility,
    _retrieved_from_chunk,
    clean_query,
    lexical_relevance_score,
    rewrite_query,
)
from app.rag.chunk_validator import validate_chunks
from app.services.semantic_rag import FusedCandidate, _minimum_score_for_intent, _semantic_relevance_score
from app.schemas.rag import DEFAULT_RAG_MIN_SIMILARITY, RagRetrieveDebugRequest, RagRetrieveRequest


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
    def setUp(self) -> None:
        super().setUp()
        # Production defaults fail closed. These focused ranking tests opt in
        # explicitly, while kill-switch coverage overrides the setting to false.
        self._retrieval_setting = patch.object(settings, "rag_student_retrieval_enabled", True)
        self._retrieval_setting.start()
        self.addCleanup(self._retrieval_setting.stop)

    @staticmethod
    def _eligibility_contract():
        return {
            "version": "test-reviewed-v1",
            "ready_for_embedding": True,
            "embedding_contract": {
                "required_chunk_metadata": [
                    "lesson_id",
                    "unit_id",
                    "source_type",
                    "printed_page_start",
                    "printed_page_end",
                    "quality_status",
                    "reviewed_metadata_version",
                ],
                "allowed_source_types": ["textbook", "solution_book"],
                "blocked_quality_statuses": ["blocked"],
            },
        }

    def test_retrieved_chunk_carries_reviewed_curriculum_metadata_from_metadata_json(self):
        raw_chunk = SimpleNamespace(
            id=91,
            source_id=4,
            content="قانون التركيز المولي C = n / V",
            source=SimpleNamespace(title="Chemistry textbook"),
            source_type="textbook",
            content_type="formula",
            page_number=110,
            unit_id=None,
            chapter_id=None,
            lesson_id=None,
            topic_id=None,
            metadata_json={
                "source_type": "textbook",
                "unit_id": "unit_04",
                "lesson_id": "unit_04_lesson_01",
                "printed_page_start": 110,
                "printed_page_end": 110,
                "quality_status": "needs_review",
                "reviewed_metadata_version": "2026-06-reviewed-v1",
            },
        )

        retrieved = _retrieved_from_chunk(raw_chunk, 0.87)  # type: ignore[arg-type]

        self.assertEqual(retrieved.unit_id, "unit_04")
        self.assertEqual(retrieved.lesson_id, "unit_04_lesson_01")
        self.assertEqual(retrieved.source_type, "textbook")
        self.assertEqual(retrieved.quality_status, "needs_review")
        self.assertEqual(retrieved.quality_warning, "This source is marked needs_review.")
        self.assertEqual(retrieved.reviewed_metadata_version, "2026-06-reviewed-v1")
        self.assertEqual(retrieved.curriculum_metadata["printed_page_start"], 110)

    def test_retrieval_eligibility_warns_for_needs_review_and_excludes_blocked(self):
        base_metadata = {
            "source_type": "textbook",
            "unit_id": "unit_04",
            "lesson_id": "unit_04_lesson_01",
            "printed_page_start": 110,
            "printed_page_end": 110,
            "reviewed_metadata_version": "test-reviewed-v1",
        }
        needs_review = SimpleNamespace(
            content="مفهوم كيميائي",
            source_type="textbook",
            extraction_method="reviewed_jsonl",
            unit_id=None,
            lesson_id=None,
            page_number=110,
            metadata_json={**base_metadata, "quality_status": "needs_review"},
        )
        blocked = SimpleNamespace(
            content="محتوى محظور",
            source_type="textbook",
            extraction_method="reviewed_jsonl",
            unit_id=None,
            lesson_id=None,
            page_number=111,
            metadata_json={**base_metadata, "quality_status": "blocked"},
        )

        review_decision = _retrieval_eligibility(needs_review, self._eligibility_contract())
        blocked_decision = _retrieval_eligibility(blocked, self._eligibility_contract())

        self.assertTrue(review_decision.rag_search_allowed)
        self.assertTrue(review_decision.warning_required)
        self.assertFalse(blocked_decision.rag_search_allowed)

    def test_rag_request_defaults_keep_raw_retrieve_strict_and_debug_permissive(self):
        retrieve_request = RagRetrieveRequest(query="ما هي الحموض؟")
        debug_request = RagRetrieveDebugRequest(query="ما هي الحموض؟")

        self.assertEqual(retrieve_request.min_similarity, DEFAULT_RAG_MIN_SIMILARITY)
        self.assertEqual(debug_request.min_similarity, 0.0)

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

    def test_acid_to_water_safety_query_prefers_warning_over_generic_acid_definition(self):
        query = "لماذا نضيف الحمض إلى الماء وليس العكس؟"
        warning_content = "تحذير: دائما أضف الحمض إلى الماء."
        acid_definition = "الحموض: مواد تُعطي عند انحلالها في الماء أيونات الهيدروجين H+."

        self.assertGreater(
            _hybrid_score(query, warning_content, vector_score=0.12),
            _hybrid_score(query, acid_definition, vector_score=0.92, intent="definition_lookup", content_type="definition"),
        )

    def test_acid_to_water_safety_rewrite_preserves_safety_intent(self):
        rewritten = rewrite_query(clean_query("لماذا نضيف الحمض إلى الماء وليس العكس؟"))

        self.assertEqual(rewritten, "تحذير أضف الحمض إلى الماء وليس العكس احتياطات السلامة حرارة تطاير غليان")
        self.assertNotIn("تعريف الحموض", rewritten)
        self.assertNotIn("أيونات الهدروجين", rewritten)
        self.assertNotIn("H+", rewritten)

    def test_safety_chunk_validation_rejects_generic_acid_definition(self):
        validations = validate_chunks(
            "لماذا نضيف الحمض إلى الماء وليس العكس؟",
            [
                chunk(52, 7, "تحذير دائما أضف الحمض إلى الماء", score=0.92),
                chunk(70, 11, "الحموض مواد تعطي عند انحلالها في الماء أيونات الهيدروجين H+.", score=0.8),
            ],
            intent="safety_question",
        )

        self.assertTrue(validations[0].valid_for_answer)
        self.assertFalse(validations[1].valid_for_answer)
        self.assertEqual(
            validations[1].rejection_reason,
            "Rejected: generic acid definition does not answer safety question.",
        )

    def test_local_fallback_answers_acid_to_water_safety_question(self):
        answer = _local_rag_answer(
            "لماذا نضيف الحمض إلى الماء وليس العكس؟",
            [
                chunk(52, 7, "تحذير دائما أضف الحمض إلى الماء", score=0.92),
                chunk(70, 11, "الحموض: مواد تُعطي عند انحلالها في الماء أيونات الهيدروجين H+.", score=0.8),
            ],
        )

        self.assertIn("أضف الحمض إلى الماء", answer)
        self.assertIn("حرارة", answer)
        self.assertIn("صفحة 7", answer)
        self.assertNotIn("الحموض هي مواد تعطي", answer)

    def test_chat_ask_safety_question_uses_safety_rule_before_rag(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="لماذا نضيف الحمض إلى الماء وليس العكس؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(result["route"], "safety_rule")
        self.assertEqual(result["diagnostics"]["intent"], "safety_question")
        self.assertTrue(result["diagnostics"]["rag_search_skipped"])
        self.assertIn("حرارة", result["answer"])
        self.assertIn("تطاير", result["answer"])
        self.assertNotIn("الحموض هي مواد", result["answer"])

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

    def test_safety_question_is_not_classified_as_acid_definition(self):
        classification = _classify_question("لماذا نضيف الحمض إلى الماء وليس العكس؟")

        self.assertEqual(classification["intent"], "safety_question")
        self.assertEqual(classification["route"], "safety_rule")

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

    def test_salt_definition_ranking_penalizes_exercise_chunks(self):
        query = rewrite_query(clean_query("ما هي الأملاح؟"))
        salt_definition = """
        نتيجة:
        يتشكل الملح من تفاعل محلول حمض مع ملح.
        يتشكل الملح من تفاعل ملح مع ملح آخر.
        جدول الأملاح يوضح أيونات الملح والصيغة الجزيئية واسم الملح.
        """
        exercise_noise = """
        أختبر نفسي: اختر الإجابة الصحيحة. مركب يصنف من الأملاح هو نترات الأمونيوم.
        السؤال الثالث: صيغة الملح المتكون من تجاذب الأيونات هي...
        """

        definition_score = _hybrid_score(
            query,
            salt_definition,
            vector_score=0.18,
            intent="definition_lookup",
            content_type="text",
        )
        exercise_score = _hybrid_score(
            query,
            exercise_noise,
            vector_score=0.82,
            intent="definition_lookup",
            content_type="exercise",
        )

        self.assertGreater(definition_score, exercise_score)

    def test_sodium_carbonate_entity_is_available_for_exact_lookup(self):
        entry = _dictionary_entry_for_question("ما صيغة كربونات الصوديوم؟", intent="formula_lookup")

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.id, "sodium_carbonate")
        self.assertEqual(entry.formula, "Na₂CO₃")

    def test_semantic_relevance_score_passes_good_definition_gate(self):
        candidate = FusedCandidate(
            chunk=chunk(
                43,
                43,
                "يتشكل الملح من تفاعل محلول حمض مع ملح. جدول الأملاح يوضح أيونات الملح والصيغة الجزيئية.",
                score=0.72,
            ),
            rrf_score=0.06,
            retrieval_score=0.72,
            origins=["original", "rewritten"],
        )

        score, reasons = _semantic_relevance_score("ما هي الأملاح؟", candidate, intent="definition_lookup")

        self.assertGreaterEqual(score, _minimum_score_for_intent("definition_lookup"))
        self.assertTrue(any("salt_evidence" in reason for reason in reasons))

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

    def test_hcl_concentration_question_uses_math_solver(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(result["route"], "math_solver")
        self.assertEqual(result["diagnostics"]["intent"], "exercise_solving")
        self.assertTrue(result["diagnostics"]["rag_search_skipped"])
        self.assertIn("Cm = m / V", result["answer"])
        self.assertIn("36.5 g/L", result["answer"])
        self.assertIn("C = n / V", result["answer"])
        self.assertIn("1 mol/L", result["answer"])
        self.assertNotIn("not_found", result["route"])

    def test_molar_concentration_question_uses_direct_definition(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما هو التركيز المولي؟",
                answer_scope="auto",
            )
        )

        self.assertIn(result["route"], {"dictionary_first", "book_knowledge"})
        self.assertIn("C = n / V", result["answer"])
        self.assertIn("mol/L", result["answer"])

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

    def test_water_formula_uses_dictionary_before_rag(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما هو رمز الماء؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(result["route"], "dictionary_first")
        self.assertEqual(result["diagnostics"]["intent"], "formula_lookup")
        self.assertIn("H₂O", result["answer"])
        self.assertNotIn("لم أجد", result["answer"])

    def test_acids_auto_answer_is_dictionary_first_not_unrelated_rag(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما هي الحموض؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(result["route"], "dictionary_first")
        self.assertIn("أيونات الهدروجين", result["answer"])
        self.assertIn("H⁺", result["answer"])
        self.assertNotIn("لم أجد", result["answer"])

    def test_bases_auto_answer_is_dictionary_first_not_objectives(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما هي الأسس؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(result["route"], "dictionary_first")
        self.assertIn("أيونات الهدروكسيد", result["answer"])
        self.assertIn("OH⁻", result["answer"])
        self.assertNotIn("الأهداف", result["answer"])
        self.assertNotIn("احتياطات", result["answer"])

    def test_litmus_color_rules_run_before_rag(self):
        acid = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما لون ورقة عباد الشمس في الوسط الحمضي؟",
                answer_scope="auto",
            )
        )
        base = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما لون ورقة عباد الشمس في محلول أساسي؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(acid["route"], "chemistry_rule")
        self.assertEqual(acid["diagnostics"]["rule_engine"], "litmus_color")
        self.assertTrue(acid["diagnostics"]["rag_search_skipped"])
        self.assertIn("الأحمر", acid["answer"])
        self.assertEqual(base["route"], "chemistry_rule")
        self.assertIn("الأزرق", base["answer"])

    def test_copper_with_dilute_sulfuric_acid_uses_activity_series_rule(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(result["route"], "chemistry_rule")
        self.assertEqual(result["diagnostics"]["rule_engine"], "activity_series")
        self.assertTrue(result["diagnostics"]["rag_search_skipped"])
        self.assertIn("لا يحدث تفاعل", result["answer"])
        self.assertIn("النحاس أقل نشاطاً من الهيدروجين", result["answer"])

    def test_calcium_oxide_water_equation_uses_book_knowledge_before_rag(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما هي معادلة تفاعل أكسيد الكالسيوم مع الماء؟",
                answer_scope="auto",
            )
        )

        self.assertEqual(result["route"], "book_knowledge")
        self.assertEqual(result["diagnostics"]["book_knowledge_key"], "cao_water")
        self.assertTrue(result["diagnostics"]["rag_search_skipped"])
        self.assertIn("CaO", result["answer"])
        self.assertIn("H₂O", result["answer"])
        self.assertIn("Ca(OH)₂", result["answer"])

    def test_arabic_followup_rephrase_reuses_previous_context_without_rag(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="اشرح بطريقة أخرى",
                action="rephrase_previous",
                previous_question="ما هي الحموض؟",
                previous_answer="الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺.",
                previous_sources=[{"page": 11, "chunk_id": 12, "chunk_type": "definition", "score": 0.9}],
            )
        )

        self.assertEqual(result["route"], "followup_rephrase")
        self.assertTrue(result["diagnostics"]["rag_search_skipped"])
        self.assertIn("H⁺", result["answer"])
        self.assertIn(11, result["page_numbers"])

    def test_english_followup_rephrase_reuses_previous_context_without_rag(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="Explain this differently with a simpler example.",
                action="rephrase_previous",
                previous_question="What are acids?",
                previous_answer="الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺.",
                previous_selected_chunks=[{"page": 11, "chunk_id": 12, "chunk_type": "definition", "score": 0.9}],
            )
        )

        self.assertEqual(result["route"], "followup_rephrase")
        self.assertTrue(result["diagnostics"]["rag_search_skipped"])
        self.assertIn("H⁺", result["answer"])
        self.assertEqual(result["diagnostics"]["selected_context"][0]["chunk_id"], 12)

    def test_audio_request_returns_text_plus_tts_unavailable_diagnostics(self):
        result = asyncio.run(
            ask_question(
                db=None,
                user_id=1,
                question="ما هو رمز الماء؟",
                answer_scope="auto",
                preferred_answer_type="audio",
            )
        )

        self.assertEqual(result["answer_type"], "audio")
        self.assertIn("H₂O", result["answer"])
        self.assertTrue(result["diagnostics"]["audio_requested_but_tts_unavailable"])
        self.assertIn("audio", {block["type"] for block in result["blocks"]})
