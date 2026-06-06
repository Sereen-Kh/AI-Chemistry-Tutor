"""Tests for the app.rag routing foundation modules."""

from __future__ import annotations

from unittest import TestCase

from app.rag.answer_verifier import verify_answer
from app.rag.arabic_normalizer import normalize_arabic
from app.rag.book_knowledge import answer_from_book_knowledge
from app.rag.chemistry_dictionary import answer_from_dictionary, find_entity
from app.rag.chemistry_rules import answer_litmus_color, answer_metal_dilute_acid
from app.rag.chunk_validator import validate_chunk
from app.rag.intent_classifier import classify_intent
from app.services.rag import RetrievedChunk


def chunk(content: str) -> RetrievedChunk:
    return RetrievedChunk(
        id=1,
        source_id=1,
        content=content,
        source="textbook",
        source_type="textbook",
        content_type="text",
        page_number=11,
        chapter_id=None,
        lesson_id=None,
        topic_id=None,
        metadata_json=None,
        similarity_score=0.8,
    )


class RagRoutingFoundationTests(TestCase):
    def test_arabic_normalizer_flattens_chemistry_notation(self):
        self.assertEqual(normalize_arabic("ما هو رمز H₂O؟"), "ما هو رمز H2O")
        self.assertEqual(normalize_arabic("ما هي الأسس؟"), "ما هي الاسس")
        self.assertIn("H+", normalize_arabic("H⁺"))
        self.assertIn("OH-", normalize_arabic("OH⁻"))

    def test_intent_classifier_detects_required_cases(self):
        self.assertEqual(classify_intent("ما هو الماء؟").intent, "definition_lookup")
        self.assertEqual(classify_intent("ما هو رمز الماء؟").intent, "formula_lookup")
        self.assertEqual(classify_intent("ما لون ورقة عباد الشمس في المحلول الحمضي؟").intent, "property_lookup")
        self.assertEqual(classify_intent("اشرح بطريقة أبسط").intent, "followup_rephrase")
        self.assertEqual(classify_intent("Explain this differently with a simpler example").intent, "followup_rephrase")

    def test_dictionary_answers_simple_direct_facts(self):
        water = answer_from_dictionary("ما هو رمز الماء؟", "formula_lookup")
        self.assertIsNotNone(water)
        assert water is not None
        self.assertIn("H₂O", water.answer)

        oxygen = answer_from_dictionary("ما هو الأكسجين؟", "definition_lookup")
        self.assertIsNotNone(oxygen)
        assert oxygen is not None
        self.assertIn("O₂", oxygen.answer)
        self.assertEqual(find_entity("ما صيغة حمض الكبريت؟").id, "sulfuric_acid")

    def test_chemistry_rules_cover_litmus_and_copper_dilute_acid(self):
        acid_litmus = answer_litmus_color("ما لون ورقة عباد الشمس في المحاليل الحمضية؟")
        base_litmus = answer_litmus_color("ما لون ورقة عباد الشمس في المحاليل الأساسية؟")
        copper = answer_metal_dilute_acid("هل يتفاعل النحاس مع حمض الكبريت الممدد؟")

        self.assertIsNotNone(acid_litmus)
        self.assertIsNotNone(base_litmus)
        self.assertIsNotNone(copper)
        assert acid_litmus and base_litmus and copper
        self.assertIn("الأحمر", acid_litmus.answer)
        self.assertIn("الأزرق", base_litmus.answer)
        self.assertIn("لا يحدث تفاعل", copper.answer)
        self.assertIn("Cu", copper.answer)
        self.assertIn("H₂SO₄", copper.answer)

    def test_book_knowledge_answers_cao_water_equation(self):
        answer = answer_from_book_knowledge("ما هي معادلة تفاعل أكسيد الكالسيوم مع الماء؟", "equation_lookup")

        self.assertIsNotNone(answer)
        assert answer is not None
        self.assertEqual(answer.key, "cao_water")
        self.assertIn("CaO", answer.answer)
        self.assertIn("H₂O", answer.answer)
        self.assertIn("Ca(OH)₂", answer.answer)

    def test_chunk_validator_rejects_water_false_match_in_acid_chunk(self):
        result = validate_chunk(
            "ما هو الماء؟",
            chunk("الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+."),
            entity="الماء",
            intent="definition_lookup",
        )

        self.assertFalse(result.valid_for_answer)
        self.assertIn("water", result.rejection_reason or "")

    def test_answer_verifier_checks_high_risk_facts(self):
        self.assertTrue(verify_answer("ما هو رمز الماء؟", "الصيغة الكيميائية للماء هي H₂O.").passed)
        self.assertFalse(verify_answer("ما هو رمز الماء؟", "الماء مهم في الكيمياء.").passed)
        self.assertTrue(
            verify_answer(
                "ما هي معادلة تفاعل أكسيد الكالسيوم مع الماء؟",
                "CaO + H₂O → Ca(OH)₂",
            ).passed
        )

