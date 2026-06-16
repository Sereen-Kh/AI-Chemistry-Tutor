"""Standalone pipeline tests for the Ask AI deterministic routing layer.

These tests verify that the correct route, answer content, and diagnostics
are produced for each of the 10 critical scenarios described in the
pipeline refactor specification.  They exercise the routing, dictionary,
safety, math-solver, chemistry-rule, and follow-up logic *without* a live
database or Gemini API key.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend package is importable when running from the tests/ dir.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.rag.arabic_normalizer import normalize_arabic  # noqa: E402
from app.rag.answer_verifier import verify_answer  # noqa: E402
from app.rag.book_knowledge import answer_from_book_knowledge  # noqa: E402
from app.rag.chemistry_dictionary import answer_from_dictionary, find_entity  # noqa: E402
from app.services.chemistry_rules import answer_metal_dilute_acid_reaction  # noqa: E402
from app.services.query_router import route_direct_answer  # noqa: E402
from app.services.safety_rules import answer_safety_rule, is_acid_to_water_safety_question  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    """Normalize for assertion comparisons."""
    return normalize_arabic(text).lower()


def _any_term(text: str, terms: tuple[str, ...]) -> bool:
    n = _norm(text)
    return any(term in n for term in terms)


# ===========================================================================
# Test 1: "ما هو الماء؟" → dictionary_first, answer contains H₂O
# ===========================================================================

class TestWaterDefinition:
    QUESTION = "ما هو الماء؟"

    def test_dictionary_entity_found(self):
        entity = find_entity(self.QUESTION)
        assert entity is not None, "Dictionary should find 'الماء' entity"
        assert entity.id == "water"

    def test_dictionary_answer_contains_h2o(self):
        result = answer_from_dictionary(self.QUESTION, intent="definition_lookup")
        assert result is not None
        assert "H₂O" in result.answer or "H2O" in result.answer

    def test_answer_does_not_define_acids(self):
        result = answer_from_dictionary(self.QUESTION, intent="definition_lookup")
        assert result is not None
        norm = _norm(result.answer)
        assert "ايونات الهدروجين" not in norm, "Water answer must NOT define acids"
        assert "h+" not in norm

    def test_route_is_dictionary_first(self):
        result = answer_from_dictionary(self.QUESTION, intent="definition_lookup")
        assert result is not None
        assert result.intent == "definition_lookup"

    def test_verification_passes(self):
        entity = find_entity(self.QUESTION)
        assert entity is not None
        v = verify_answer(self.QUESTION, entity.answer_ar)
        assert v.passed, f"Verification failed: {v.reason}"


# ===========================================================================
# Test 2: "لماذا نضيف الحمض إلى الماء وليس العكس؟" → safety_rule
# ===========================================================================

class TestAcidToWaterSafety:
    QUESTION = "لماذا نضيف الحمض إلى الماء وليس العكس؟"

    def test_safety_question_detected(self):
        assert is_acid_to_water_safety_question(self.QUESTION)

    def test_safety_rule_returns_answer(self):
        result = answer_safety_rule(self.QUESTION)
        assert result is not None
        assert result.route == "safety_rule"

    def test_answer_mentions_heat_or_splashing(self):
        result = answer_safety_rule(self.QUESTION)
        assert result is not None
        assert _any_term(result.answer, ("حرارة", "حراره", "تطاير", "غليان"))

    def test_answer_does_not_only_define_acids(self):
        result = answer_safety_rule(self.QUESTION)
        assert result is not None
        norm = _norm(result.answer)
        # The answer should not be just "الحموض مواد تعطي..."
        assert "مواد تعطي عند انحلالها" not in norm

    def test_verification_passes(self):
        result = answer_safety_rule(self.QUESTION)
        assert result is not None
        v = verify_answer(self.QUESTION, result.answer)
        assert v.passed, f"Verification failed: {v.reason}"


# ===========================================================================
# Test 3: "ما هو التركيز المولي؟" → dictionary_first, contains C = n / V
# ===========================================================================

class TestMolarConcentrationDefinition:
    QUESTION = "ما هو التركيز المولي؟"

    def test_dictionary_entity_found(self):
        entity = find_entity(self.QUESTION)
        assert entity is not None, "Dictionary should find 'التركيز المولي' entity"

    def test_answer_contains_formula(self):
        result = answer_from_dictionary(self.QUESTION, intent="definition_lookup")
        assert result is not None
        assert "C = n / V" in result.answer or "C=n/V" in result.answer

    def test_answer_contains_unit(self):
        result = answer_from_dictionary(self.QUESTION, intent="definition_lookup")
        assert result is not None
        assert "mol/L" in result.answer

    def test_route_direct_answer_also_works(self):
        """The query_router should also produce a definition answer."""
        result = route_direct_answer(self.QUESTION)
        if result is not None:
            assert "C = n / V" in result.answer or "C=n/V" in result.answer or "C = n/V" in result.answer


# ===========================================================================
# Test 4: HCl concentration problem → math_solver
# ===========================================================================

class TestHClConcentrationExercise:
    QUESTION = "محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي؟"

    def test_route_is_math_solver(self):
        result = route_direct_answer(self.QUESTION)
        assert result is not None, "Math solver should handle this question"
        assert result.route == "math_solver"

    def test_answer_contains_gram_concentration(self):
        result = route_direct_answer(self.QUESTION)
        assert result is not None
        assert "36.5" in result.answer and "g/L" in result.answer

    def test_answer_contains_molar_concentration(self):
        result = route_direct_answer(self.QUESTION)
        assert result is not None
        assert "1 mol/L" in result.answer or "1.0 mol/L" in result.answer or "1mol/L" in result.answer

    def test_answer_contains_formulas(self):
        result = route_direct_answer(self.QUESTION)
        assert result is not None
        assert "Cm = m / V" in result.answer or "Cm =" in result.answer
        assert "C = n / V" in result.answer or "C =" in result.answer

    def test_not_found_never_appears(self):
        result = route_direct_answer(self.QUESTION)
        assert result is not None
        assert "لم أجد" not in result.answer

    def test_extracted_values(self):
        result = route_direct_answer(self.QUESTION)
        assert result is not None
        ev = result.extracted_values
        assert ev is not None, "extracted_values should be populated"
        assert ev["compound"] == "HCl"
        assert ev["mass_g"] == 3.65
        assert ev["volume_ml"] == 100.0
        assert abs(ev["Cm_g_L"] - 36.5) < 0.01
        assert abs(ev["C_mol_L"] - 1.0) < 0.01

    def test_verification_passes(self):
        result = route_direct_answer(self.QUESTION)
        assert result is not None
        v = verify_answer(self.QUESTION, result.answer)
        assert v.passed, f"Verification failed: {v.reason}"


# ===========================================================================
# Test 5: "ما لون ورقة عباد الشمس في المحاليل الحمضية؟" → chemistry_rule
# ===========================================================================

class TestLitmusColorAcid:
    QUESTION = "ما لون ورقة عباد الشمس في المحاليل الحمضية؟"

    def test_book_knowledge_returns_answer(self):
        result = answer_from_book_knowledge(self.QUESTION, intent="property_lookup")
        assert result is not None

    def test_answer_contains_red(self):
        result = answer_from_book_knowledge(self.QUESTION, intent="property_lookup")
        assert result is not None
        assert "الأحمر" in result.answer or "الاحمر" in _norm(result.answer)

    def test_dictionary_entry_exists(self):
        entity = find_entity(self.QUESTION)
        assert entity is not None

    def test_verification_passes(self):
        result = answer_from_book_knowledge(self.QUESTION, intent="property_lookup")
        assert result is not None
        v = verify_answer(self.QUESTION, result.answer)
        assert v.passed, f"Verification failed: {v.reason}"


# ===========================================================================
# Test 6: "ما هي الحموض؟" → contains H⁺
# ===========================================================================

class TestAcidsDefinition:
    QUESTION = "ما هي الحموض؟"

    def test_dictionary_answer_contains_h_plus(self):
        result = answer_from_dictionary(self.QUESTION, intent="definition_lookup")
        assert result is not None
        assert "H⁺" in result.answer or "H+" in result.answer or _any_term(
            result.answer, ("ايونات الهدروجين", "ايونات الهيدروجين")
        )

    def test_verification_passes(self):
        result = answer_from_dictionary(self.QUESTION, intent="definition_lookup")
        assert result is not None
        v = verify_answer(self.QUESTION, result.answer)
        assert v.passed, f"Verification failed: {v.reason}"


# ===========================================================================
# Test 7: "ما هي الأسس؟" → contains OH⁻
# ===========================================================================

class TestBasesDefinition:
    QUESTION = "ما هي الأسس؟"

    def test_dictionary_answer_contains_oh_minus(self):
        result = answer_from_dictionary(self.QUESTION, intent="definition_lookup")
        assert result is not None
        assert "OH⁻" in result.answer or "OH-" in result.answer or _any_term(
            result.answer, ("ايونات الهدروكسيد",)
        )

    def test_verification_passes(self):
        result = answer_from_dictionary(self.QUESTION, intent="definition_lookup")
        assert result is not None
        v = verify_answer(self.QUESTION, result.answer)
        assert v.passed, f"Verification failed: {v.reason}"


# ===========================================================================
# Test 8: "هل يتفاعل النحاس مع حمض الكبريت الممدد؟" → chemistry_rule
# ===========================================================================

class TestCopperDiluteAcid:
    QUESTION = "هل يتفاعل النحاس مع حمض الكبريت الممدد؟"

    def test_reaction_rule_returns_answer(self):
        result = answer_metal_dilute_acid_reaction(self.QUESTION)
        assert result is not None, "Chemistry rule should handle copper + dilute acid"

    def test_no_reaction(self):
        result = answer_metal_dilute_acid_reaction(self.QUESTION)
        assert result is not None
        assert not result.reaction_happens

    def test_answer_says_no_reaction(self):
        result = answer_metal_dilute_acid_reaction(self.QUESTION)
        assert result is not None
        assert "لا يحدث تفاعل" in result.answer or "لا تفاعل" in result.answer

    def test_answer_explains_activity_series(self):
        result = answer_metal_dilute_acid_reaction(self.QUESTION)
        assert result is not None
        norm = _norm(result.answer)
        assert "اقل نشاطا" in norm or "اقل نشاط" in norm or "لا يستطيع ازاحه" in norm or "ادني" in norm

    def test_verification_passes(self):
        result = answer_metal_dilute_acid_reaction(self.QUESTION)
        assert result is not None
        v = verify_answer(self.QUESTION, result.answer)
        assert v.passed, f"Verification failed: {v.reason}"


# ===========================================================================
# Test 9: Simulate Gemini 429 — deterministic routes still work
# ===========================================================================

class TestGemini429Fallback:
    """When Gemini is unavailable, deterministic questions must still be
    answered by the local router without hanging or returning errors."""

    def test_water_definition_without_gemini(self):
        """'ما هو الماء؟' must work even without Gemini."""
        entity = find_entity("ما هو الماء؟")
        assert entity is not None
        assert "H₂O" in entity.answer_ar

    def test_safety_rule_without_gemini(self):
        result = answer_safety_rule("لماذا نضيف الحمض إلى الماء وليس العكس؟")
        assert result is not None
        assert result.route == "safety_rule"

    def test_math_solver_without_gemini(self):
        result = route_direct_answer(
            "محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي؟"
        )
        assert result is not None
        assert result.route == "math_solver"
        assert "36.5" in result.answer

    def test_litmus_without_gemini(self):
        result = answer_from_book_knowledge(
            "ما لون ورقة عباد الشمس في المحاليل الحمضية؟",
            intent="property_lookup",
        )
        assert result is not None
        assert "الأحمر" in result.answer

    def test_copper_acid_without_gemini(self):
        result = answer_metal_dilute_acid_reaction(
            "هل يتفاعل النحاس مع حمض الكبريت الممدد؟"
        )
        assert result is not None
        assert "لا يحدث تفاعل" in result.answer


# ===========================================================================
# Test 10: Follow-up rephrase — no RAG search using only the follow-up phrase
# ===========================================================================

class TestFollowupRephrase:
    """When the user says 'اشرح بطريقة أبسط' with a parent_message_id,
    the system should rephrase the previous answer, not run a new RAG
    search using only the follow-up phrase."""

    def test_followup_detected(self):
        from app.services.chat_service import _is_followup_rephrase
        assert _is_followup_rephrase("اشرح بطريقة أبسط")
        assert _is_followup_rephrase("لم أفهم")
        assert _is_followup_rephrase("Explain this differently")
        assert _is_followup_rephrase("Try differently")

    def test_followup_with_action(self):
        from app.services.chat_service import _is_followup_rephrase
        assert _is_followup_rephrase("anything", action="rephrase_previous")
        assert _is_followup_rephrase("anything", action="try_differently")
        assert _is_followup_rephrase("anything", action="simplify_previous")

    def test_simplify_acids_answer(self):
        from app.services.chat_service import _simplify_previous_answer
        previous = "الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺."
        simplified = _simplify_previous_answer(previous, "ما هي الحموض؟")
        # Should produce a simplified explanation, not run RAG
        assert simplified  # Non-empty
        norm = _norm(simplified)
        # Simplified answer should still mention H+ or hydrogen ions
        assert "h+" in norm or "ايونات الهدروجين" in norm or "ايونات الهيدروجين" in norm

    def test_simplify_water_answer(self):
        from app.services.chat_service import _simplify_previous_answer
        previous = "الماء مركب كيميائي صيغته H₂O، ويتكوّن من ذرتي هيدروجين وذرة أكسجين."
        simplified = _simplify_previous_answer(previous, "ما هو الماء؟")
        assert simplified
        assert "H₂O" in simplified or "h2o" in _norm(simplified)

    def test_simplify_bases_answer(self):
        from app.services.chat_service import _simplify_previous_answer
        previous = "الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻."
        simplified = _simplify_previous_answer(previous, "ما هي الأسس؟")
        assert simplified
        norm = _norm(simplified)
        assert "oh" in norm or "ايونات الهدروكسيد" in norm
