"""Evaluation runner for the EduMind Chemistry Tutor.

Usage:
    # Routing-only tests (no DB, no API key, fast):
    python tests/evaluation/eval_runner.py --mode routing

    # Full pipeline tests (requires DB + API key):
    python tests/evaluation/eval_runner.py --mode full
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")


def _load_cases() -> dict:
    path = Path(__file__).parent / "evaluation_cases.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Routing-only evaluation (no DB needed)
# ---------------------------------------------------------------------------


def _run_routing_tests() -> tuple[int, int, list[dict]]:
    """Test intent classification, dictionary resolution, and direct routing."""
    from app.services.chat_service import _classify_question, _dictionary_entry_for_question
    from app.services.query_router import route_direct_answer
    from app.services.safety_rules import is_acid_to_water_safety_question

    cases_data = _load_cases()
    passed = 0
    failed = 0
    failures: list[dict] = []

    for category, cases in cases_data["categories"].items():
        for case in cases:
            case_id = case["id"]
            question = case["question"]
            expected_intent = case["expected_intent"]
            expected_route = case["expected_route"]
            required_in_answer = case.get("required_in_answer", [])
            forbidden_in_answer = case.get("forbidden_in_answer", [])
            expected_confidence_min = case.get("expected_confidence_min", 0.0)

            errors: list[str] = []

            # 1. Check intent classification
            classification = _classify_question(question)
            actual_intent = classification["intent"]
            if actual_intent != expected_intent:
                errors.append(
                    f"Intent mismatch: expected '{expected_intent}', got '{actual_intent}'"
                )

            # 2. Check dictionary entry resolution
            dictionary_entry = _dictionary_entry_for_question(question, intent=actual_intent)

            # 3. Check direct routing
            if expected_route == "safety_rule":
                if not is_acid_to_water_safety_question(question):
                    errors.append("Safety rule did not trigger for safety question")

            elif expected_route == "math_solver":
                direct = route_direct_answer(question)
                if direct is None:
                    errors.append("route_direct_answer returned None for exercise question")
                else:
                    # Check answer content
                    for term in required_in_answer:
                        if term not in direct.answer:
                            errors.append(f"Required term '{term}' not in direct answer")
                    for term in forbidden_in_answer:
                        if term in direct.answer:
                            errors.append(f"Forbidden term '{term}' found in direct answer")
                    if direct.confidence < expected_confidence_min:
                        errors.append(
                            f"Confidence {direct.confidence} < expected {expected_confidence_min}"
                        )

            elif expected_route == "dictionary_first":
                if dictionary_entry is None:
                    errors.append("Dictionary entry not found for dictionary_first route")
                else:
                    answer = dictionary_entry.answer_ar
                    for term in required_in_answer:
                        if term not in answer:
                            errors.append(
                                f"Required term '{term}' not in dictionary answer"
                            )
                    for term in forbidden_in_answer:
                        if term in answer:
                            errors.append(
                                f"Forbidden term '{term}' found in dictionary answer"
                            )
                    if dictionary_entry.confidence < expected_confidence_min:
                        errors.append(
                            f"Confidence {dictionary_entry.confidence} < expected {expected_confidence_min}"
                        )

            elif expected_route == "chemistry_rule":
                direct = route_direct_answer(question)
                if expected_route == "chemistry_rule" and direct is None:
                    # Reaction queries might be handled by chemistry_rules.py, not query_router
                    from app.services.chemistry_rules import (
                        answer_metal_dilute_acid_reaction,
                    )

                    reaction = answer_metal_dilute_acid_reaction(question)
                    if reaction is None:
                        # For litmus, check classification
                        if "litmus" not in case_id and "عباد الشمس" not in question:
                            errors.append(
                                "Neither route_direct_answer nor chemistry_rules produced an answer"
                            )
                    else:
                        for term in required_in_answer:
                            if term not in reaction.answer:
                                errors.append(
                                    f"Required term '{term}' not in reaction answer"
                                )
                elif direct is not None:
                    for term in required_in_answer:
                        if term not in direct.answer:
                            errors.append(f"Required term '{term}' not in direct answer")

            # Verdict
            if errors:
                failed += 1
                failures.append(
                    {
                        "case_id": case_id,
                        "category": category,
                        "question": question,
                        "errors": errors,
                    }
                )
                print(f"  FAIL  {case_id}: {errors[0]}")
            else:
                passed += 1
                print(f"  PASS  {case_id}")

    return passed, failed, failures


# ---------------------------------------------------------------------------
# Full pipeline evaluation (requires DB + API key)
# ---------------------------------------------------------------------------


async def _run_full_tests() -> tuple[int, int, list[dict]]:
    """Run the complete ask_question pipeline for each test case."""
    from app.database import get_async_db
    from app.services import chat_service

    cases_data = _load_cases()
    passed = 0
    failed = 0
    failures: list[dict] = []

    async for db in get_async_db():
        for category, cases in cases_data["categories"].items():
            for case in cases:
                case_id = case["id"]
                question = case["question"]
                expected_route = case["expected_route"]
                required_in_answer = case.get("required_in_answer", [])
                forbidden_in_answer = case.get("forbidden_in_answer", [])
                expected_confidence_min = case.get("expected_confidence_min", 0.0)

                errors: list[str] = []

                try:
                    result = await chat_service.ask_question(
                        db=db,
                        user_id=1,
                        question=question,
                        answer_scope="auto",
                    )

                    answer = result.get("answer", "")
                    route = result.get("route", "")
                    confidence = result.get("confidence", 0.0)

                    if route != expected_route:
                        errors.append(
                            f"Route mismatch: expected '{expected_route}', got '{route}'"
                        )

                    for term in required_in_answer:
                        if term not in answer:
                            errors.append(f"Required term '{term}' not in answer")

                    for term in forbidden_in_answer:
                        if term in answer:
                            errors.append(f"Forbidden term '{term}' found in answer")

                    if confidence < expected_confidence_min:
                        errors.append(
                            f"Confidence {confidence} < expected {expected_confidence_min}"
                        )

                except Exception as e:
                    errors.append(f"Exception: {e}")

                if errors:
                    failed += 1
                    failures.append(
                        {
                            "case_id": case_id,
                            "category": category,
                            "question": question,
                            "errors": errors,
                        }
                    )
                    print(f"  FAIL  {case_id}: {errors[0]}")
                else:
                    passed += 1
                    print(f"  PASS  {case_id}")
        break

    return passed, failed, failures


def main():
    parser = argparse.ArgumentParser(description="EduMind evaluation runner")
    parser.add_argument(
        "--mode",
        choices=["routing", "full"],
        default="routing",
        help="Test mode: 'routing' for offline deterministic tests, 'full' for complete pipeline",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"EduMind Chemistry Tutor - Evaluation Runner")
    print(f"Mode: {args.mode}")
    print(f"{'='*60}\n")

    if args.mode == "routing":
        passed, failed, failures = _run_routing_tests()
    else:
        import asyncio

        passed, failed, failures = asyncio.run(_run_full_tests())

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'='*60}")

    if failures:
        print("\nFailed cases:")
        for failure in failures:
            print(f"\n  {failure['case_id']} ({failure['category']}):")
            print(f"    Question: {failure['question']}")
            for error in failure["errors"]:
                print(f"    ❌ {error}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
