"""Tests for deterministic Grade 9 chemistry rules."""

from __future__ import annotations

from unittest import TestCase

from app.services.chemistry_rules import answer_metal_dilute_acid_reaction, detect_metal_and_acid


class ChemistryRulesTests(TestCase):
    def test_detects_arabic_metal_and_acid_names(self):
        metal, acid = detect_metal_and_acid("ما هي معادلة النحاس مع حمض الكبريت الممدد؟")

        self.assertIsNotNone(metal)
        self.assertIsNotNone(acid)
        assert metal is not None
        assert acid is not None
        self.assertEqual(metal.symbol, "Cu")
        self.assertEqual(acid.key, "h2so4")

    def test_copper_with_dilute_sulfuric_acid_does_not_react(self):
        result = answer_metal_dilute_acid_reaction(
            "ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟"
        )

        self.assertIsNotNone(result)
        assert result is not None
        self.assertFalse(result.reaction_happens)
        self.assertIn("لا يحدث تفاعل", result.answer)
        self.assertIn("أقل نشاطاً من الهيدروجين", result.answer)
        self.assertIn("Cu + H2SO4(dilute)", result.equation)
        self.assertGreaterEqual(result.confidence, 0.65)

    def test_zinc_with_dilute_sulfuric_acid_produces_hydrogen(self):
        result = answer_metal_dilute_acid_reaction("اكتب تفاعل الزنك مع حمض الكبريت الممدد")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.reaction_happens)
        self.assertIn("Zn + H2SO4(dilute) → ZnSO4 + H2", result.equation)
        self.assertIn("يحدث تفاعل", result.answer)
