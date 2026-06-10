"""Tests for deterministic query routing before generic RAG."""

from __future__ import annotations

from unittest import TestCase

from app.services.query_router import normalize_query, route_direct_answer


class QueryRouterTests(TestCase):
    def test_normalizes_arabic_and_formula_notation(self):
        self.assertEqual(normalize_query("H₂O"), "h2o")
        self.assertIn("الاول", normalize_query("الدَّرس الأوَّل"))

    def test_water_formula_is_answered_without_generic_retrieval(self):
        result = route_direct_answer("ما هو الرمز الكيميائي للماء؟")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.intent, "formula_lookup")
        self.assertIn("H₂O", result.answer)
        self.assertEqual(result.confidence, 1.0)

    def test_ambiguous_water_equation_asks_clarification(self):
        result = route_direct_answer("معادلة الماء؟")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.intent, "clarification")
        self.assertIn("غير محدد", result.answer)
        self.assertIn("تفكك الماء", result.answer)
        self.assertEqual(result.page_numbers, [])

    def test_water_decomposition_equation_is_direct(self):
        result = route_direct_answer("ما معادلة تفكك الماء؟")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.intent, "equation_lookup")
        self.assertIn("2H₂O", result.answer)
        self.assertIn(30, result.page_numbers)

    def test_copper_dilute_sulfuric_acid_reaction_is_direct(self):
        result = route_direct_answer("ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.intent, "reaction_query")
        self.assertIn("لا يحدث تفاعل", result.answer)
        self.assertNotIn("الحموض هي مواد", result.answer)
        self.assertGreaterEqual(result.confidence, 0.65)

    def test_lesson_one_navigation_uses_book_structure(self):
        result = route_direct_answer("اعطني ماذا يحتوي الدرس الاول؟")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.intent, "lesson_navigation")
        self.assertIn("المحاليل المائية", result.answer)
        self.assertIn("يتعرّف المحلول المائي", result.answer)
        self.assertIn(2, result.page_numbers)

    def test_hcl_concentration_exercise_is_math_solver(self):
        result = route_direct_answer("محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي؟")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.intent, "exercise_solving")
        self.assertEqual(result.route, "math_solver")
        self.assertIn("Cm = m / V", result.answer)
        self.assertIn("36.5 g/L", result.answer)
        self.assertIn("C = n / V", result.answer)
        self.assertIn("1 mol/L", result.answer)

    def test_molar_concentration_definition_is_direct(self):
        result = route_direct_answer("ما هو التركيز المولي؟")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.route, "dictionary_first")
        self.assertIn("C = n / V", result.answer)
        self.assertIn("mol/L", result.answer)
