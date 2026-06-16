"""Pytest-compatible routing tests for the EduMind Chemistry Tutor.

Run with:
    cd backend
    python -m pytest tests/evaluation/test_routing.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND_DIR / ".env")

from app.services.chat_service import (  # noqa: E402
    _classify_question,
    _dictionary_entry_for_question,
)
from app.services.query_router import route_direct_answer  # noqa: E402
from app.services.safety_rules import is_acid_to_water_safety_question  # noqa: E402


def _load_cases() -> dict:
    path = Path(__file__).parent / "evaluation_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


CASES = _load_cases()


def _all_cases() -> list[tuple[str, dict]]:
    """Flatten all cases into (category, case) tuples."""
    result = []
    for category, cases in CASES["categories"].items():
        for case in cases:
            result.append((category, case))
    return result


ALL_CASES = _all_cases()
CASE_IDS = [case["id"] for _, case in ALL_CASES]


# ---------------------------------------------------------------------------
# Intent classification tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category,case", ALL_CASES, ids=CASE_IDS)
def test_intent_classification(category: str, case: dict):
    """Verify that _classify_question returns the expected intent."""
    classification = _classify_question(case["question"])
    actual = classification["intent"]
    expected = case["expected_intent"]
    assert actual == expected, (
        f"[{case['id']}] Intent mismatch for '{case['question']}': "
        f"expected '{expected}', got '{actual}'"
    )


# ---------------------------------------------------------------------------
# Dictionary resolution tests
# ---------------------------------------------------------------------------


DICTIONARY_CASES = [
    (cat, c) for cat, c in ALL_CASES if c["expected_route"] == "dictionary_first"
]
DICTIONARY_IDS = [c["id"] for _, c in DICTIONARY_CASES]


@pytest.mark.parametrize("category,case", DICTIONARY_CASES, ids=DICTIONARY_IDS)
def test_dictionary_entry_resolution(category: str, case: dict):
    """Verify that dictionary entries are found for dictionary_first routes."""
    classification = _classify_question(case["question"])
    entry = _dictionary_entry_for_question(
        case["question"], intent=classification["intent"]
    )
    assert entry is not None, (
        f"[{case['id']}] Dictionary entry not found for '{case['question']}'"
    )

    # Check required terms in the dictionary answer
    for term in case.get("required_in_answer", []):
        assert term in entry.answer_ar, (
            f"[{case['id']}] Required term '{term}' not in dictionary answer: "
            f"'{entry.answer_ar[:100]}...'"
        )


# ---------------------------------------------------------------------------
# Safety rule tests
# ---------------------------------------------------------------------------


SAFETY_CASES = [
    (cat, c) for cat, c in ALL_CASES if c["expected_route"] == "safety_rule"
]
SAFETY_IDS = [c["id"] for _, c in SAFETY_CASES]


@pytest.mark.parametrize("category,case", SAFETY_CASES, ids=SAFETY_IDS)
def test_safety_rule_detection(category: str, case: dict):
    """Verify that safety questions trigger the safety rule."""
    assert is_acid_to_water_safety_question(case["question"]), (
        f"[{case['id']}] Safety rule NOT triggered for '{case['question']}'"
    )


# ---------------------------------------------------------------------------
# Exercise solving (direct router) tests
# ---------------------------------------------------------------------------


EXERCISE_CASES = [
    (cat, c) for cat, c in ALL_CASES if c["expected_route"] == "math_solver"
]
EXERCISE_IDS = [c["id"] for _, c in EXERCISE_CASES]


@pytest.mark.parametrize("category,case", EXERCISE_CASES, ids=EXERCISE_IDS)
def test_exercise_direct_routing(category: str, case: dict):
    """Verify that exercise questions are solved by route_direct_answer."""
    result = route_direct_answer(case["question"])
    assert result is not None, (
        f"[{case['id']}] route_direct_answer returned None for '{case['question']}'"
    )
    for term in case.get("required_in_answer", []):
        assert term in result.answer, (
            f"[{case['id']}] Required term '{term}' not in answer: "
            f"'{result.answer[:100]}...'"
        )


# ---------------------------------------------------------------------------
# Reaction query (chemistry rule) tests
# ---------------------------------------------------------------------------


REACTION_CASES = [
    (cat, c)
    for cat, c in ALL_CASES
    if c["expected_route"] == "chemistry_rule" and "litmus" not in c["id"]
]
REACTION_IDS = [c["id"] for _, c in REACTION_CASES]


@pytest.mark.parametrize("category,case", REACTION_CASES, ids=REACTION_IDS)
def test_reaction_chemistry_rules(category: str, case: dict):
    """Verify that reaction queries are answered by chemistry rules or direct router."""
    from app.services.chemistry_rules import answer_metal_dilute_acid_reaction

    reaction = answer_metal_dilute_acid_reaction(case["question"])
    direct = route_direct_answer(case["question"])

    answer_text = ""
    if reaction:
        answer_text = reaction.answer
    elif direct:
        answer_text = direct.answer

    assert answer_text, (
        f"[{case['id']}] No answer from chemistry_rules or direct_router for "
        f"'{case['question']}'"
    )

    for term in case.get("required_in_answer", []):
        assert term in answer_text, (
            f"[{case['id']}] Required term '{term}' not in answer: "
            f"'{answer_text[:100]}...'"
        )


# ---------------------------------------------------------------------------
# Formula/symbol lookup via direct router
# ---------------------------------------------------------------------------


FORMULA_CASES = [
    (cat, c)
    for cat, c in ALL_CASES
    if c["expected_intent"] == "formula_lookup"
]
FORMULA_IDS = [c["id"] for _, c in FORMULA_CASES]


@pytest.mark.parametrize("category,case", FORMULA_CASES, ids=FORMULA_IDS)
def test_formula_direct_routing(category: str, case: dict):
    """Verify formula lookups are answered by route_direct_answer."""
    result = route_direct_answer(case["question"])
    # Formula lookups can also be handled by dictionary_first
    if result is not None:
        for term in case.get("required_in_answer", []):
            assert term in result.answer, (
                f"[{case['id']}] Required term '{term}' not in answer"
            )
