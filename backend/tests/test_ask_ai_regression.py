"""Book-wide deterministic Ask AI grounding regression tests."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.ask_ai_regression_harness import (
    DATASET_PATH,
    evaluate_answer,
    load_book_cases,
    repeat_count_from_env,
    run_deterministic_text_suite,
)
from scripts.run_ask_ai_regression_suite import (
    ASK_AI_LIVE_NOT_AUTHORIZED,
    ASK_AI_RAG_INDEX_NOT_READY,
    _live_prerequisite_blocker,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
SUBTOPICS_PATH = REPO_ROOT / "data" / "processed" / "textbook" / "textbook_subtopics.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_ask_ai_gold_dataset_is_current_and_covers_all_reviewed_subtopics():
    result = subprocess.run(
        [sys.executable, "scripts/build_ask_ai_book_questions.py", "--check"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    cases = load_book_cases(DATASET_PATH)
    subtopics = _read_jsonl(SUBTOPICS_PATH)
    case_subtopic_ids = {case.get("source_subtopic_id") for case in cases if case.get("source_subtopic_id")}
    reviewed_subtopic_ids = {row["subtopic_id"] for row in subtopics}
    assert case_subtopic_ids == reviewed_subtopic_ids
    assert len(reviewed_subtopic_ids) == 52
    assert len(cases) == 53
    assert {case["expected_unit_id"] for case in cases} == {"unit_04", "unit_05", "unit_06"}
    assert len({case["expected_lesson_id"] for case in cases}) == 9
    assert any(case["question_ar"] == "لماذا نضيف الحمض إلى الماء وليس العكس؟" for case in cases)


def test_every_reviewed_question_and_paraphrase_is_grounded_and_repeatable():
    cases = load_book_cases()
    result = run_deterministic_text_suite(cases, repeat_count=repeat_count_from_env())

    assert result["repeat_count"] == repeat_count_from_env()
    assert result["total_executions"] == result["question_variants"] * result["repeat_count"]
    assert result["pass_rate"] == 1.0, result["failed_cases"][:20]
    assert result["citation_metadata_completeness"] == 1.0, result["failed_cases"][:20]
    assert result["expected_page_hit_rate"] == 1.0, result["failed_cases"][:20]
    assert result["contradiction_count"] == 0, result["failed_cases"][:20]
    assert result["unstable_source_count"] == 0, result["failed_cases"][:20]
    assert result["blocked_stale_citation_count"] == 0, result["failed_cases"][:20]
    assert result["out_of_scope_passed"] == result["out_of_scope_executions"]
    assert not result["failed_cases"]


def test_regression_validator_rejects_blocked_and_stale_citations():
    case = load_book_cases()[0]
    source = {
        "chunk_id": 1,
        "source_id": 2,
        "source_type": case["expected_source_type"],
        "page_number": case["expected_printed_pages"][0],
        "unit_id": case["expected_unit_id"],
        "lesson_id": case["expected_lesson_id"],
        "quality_status": "blocked",
        "quality_warning": None,
        "reviewed_metadata_version": case["reviewed_metadata_version"],
        "similarity_score": 0.9,
        "curriculum_metadata": {
            "printed_page_start": case["expected_printed_pages"][0],
            "printed_page_end": case["expected_printed_pages"][0],
            "stale": True,
        },
    }
    payload = {"answer": f"إجابة موثقة عن {case['expected_concepts'][0]}", "sources": [source]}

    result = evaluate_answer(case, payload)

    assert result["passed"] is False
    assert "BLOCKED_OR_STALE_CITATION" in result["failures"]
    assert result["blocked_stale_count"] == 1


def test_regression_validator_requires_warning_for_needs_review_sources():
    case = load_book_cases()[0]
    page = case["expected_printed_pages"][0]
    source = {
        "chunk_id": 1,
        "source_id": 2,
        "source_type": case["expected_source_type"],
        "page_number": page,
        "unit_id": case["expected_unit_id"],
        "lesson_id": case["expected_lesson_id"],
        "quality_status": "needs_review",
        "quality_warning": None,
        "reviewed_metadata_version": case["reviewed_metadata_version"],
        "similarity_score": 0.9,
        "curriculum_metadata": {
            "printed_page_start": page,
            "printed_page_end": page,
            "stale": False,
        },
    }
    payload = {"answer": f"إجابة موثقة عن {case['expected_concepts'][0]}", "sources": [source]}

    result = evaluate_answer(case, payload)

    assert result["passed"] is False
    assert "NEEDS_REVIEW_WARNING_MISSING" in result["failures"]


def test_live_regression_is_not_authorized_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("RUN_ASK_AI_INTEGRATION", raising=False)

    blocker = _live_prerequisite_blocker({"live_status": "ready"})

    assert blocker == ASK_AI_LIVE_NOT_AUTHORIZED


def test_live_regression_stops_when_embedding_index_is_incomplete(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RUN_ASK_AI_INTEGRATION", "1")

    blocker = _live_prerequisite_blocker({"live_status": "blocked"})

    assert blocker == ASK_AI_RAG_INDEX_NOT_READY
