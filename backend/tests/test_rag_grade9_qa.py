"""Deterministic API QA suite for the Grade 9 Chemistry RAG system."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user_id
from app.main import app
from app.services.rag import clean_query, rewrite_query
from scripts.rag_qa_harness import (
    chunk_previews,
    contains_term,
    install_deterministic_api_overrides,
    load_cases,
    missing_terms,
    normalize_for_assertion,
    present_terms,
    route_exists,
)

CASES = load_cases()


def _target_cases(endpoint_target: str) -> list[dict[str, Any]]:
    return [case for case in CASES if endpoint_target in case["endpoint_targets"]]


def _case_id(case: dict[str, Any]) -> str:
    return str(case["id"])


def _failure_message(
    case: dict[str, Any],
    *,
    actual_answer: str = "",
    chunks: list[dict[str, Any]] | None = None,
    payload: dict[str, Any] | None = None,
) -> str:
    return (
        f"RAG QA failure\n"
        f"case_id={case['id']}\n"
        f"category={case['category']}\n"
        f"question={case['question']}\n"
        f"expected_keywords={case['expected_answer_keywords']}\n"
        f"forbidden_keywords={case['forbidden_keywords']}\n"
        f"expected_behavior={case['expected_behavior']}\n"
        f"actual_answer={actual_answer}\n"
        f"retrieved_chunk_previews={chunk_previews(chunks or [])}\n"
        f"payload={payload}"
    )


def _assert_no_forbidden_keywords(case: dict[str, Any], text: str, *, chunks=None, payload=None) -> None:
    forbidden = present_terms(text, case["forbidden_keywords"])
    assert not forbidden, _failure_message(case, actual_answer=text, chunks=chunks, payload=payload)


def _assert_expected_keywords(case: dict[str, Any], text: str, *, chunks=None, payload=None) -> None:
    missing = missing_terms(text, case["expected_answer_keywords"])
    assert not missing, _failure_message(case, actual_answer=text, chunks=chunks, payload=payload)


def _assert_source_topics(case: dict[str, Any], text: str, *, chunks=None, payload=None) -> None:
    missing = missing_terms(text, case["expected_source_topics"])
    assert not missing, _failure_message(case, actual_answer=text, chunks=chunks, payload=payload)


def _assert_retrieve_source_metadata(case: dict[str, Any], chunks: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    assert chunks, _failure_message(case, chunks=chunks, payload=payload)
    top = chunks[0]
    for field in ("id", "source_id", "page_number", "similarity_score"):
        assert top.get(field) is not None, _failure_message(case, chunks=chunks, payload=payload)
    assert float(top["similarity_score"]) >= float(case["min_confidence"]), _failure_message(
        case, chunks=chunks, payload=payload
    )


def _assert_chat_source_metadata(case: dict[str, Any], sources: list[dict[str, Any]], payload: dict[str, Any]) -> None:
    assert sources, _failure_message(case, actual_answer=payload.get("answer", ""), chunks=sources, payload=payload)
    top = sources[0]
    for field in ("chunk_id", "source_id", "page_number", "similarity_score"):
        assert top.get(field) is not None, _failure_message(
            case, actual_answer=payload.get("answer", ""), chunks=sources, payload=payload
        )


def _assert_homework_source_metadata(
    case: dict[str, Any], source_chunks: list[dict[str, Any]], payload: dict[str, Any]
) -> None:
    assert source_chunks, _failure_message(
        case, actual_answer=payload.get("solution", ""), chunks=source_chunks, payload=payload
    )
    top = source_chunks[0]
    for field in ("chunk_id", "source_id", "page_number", "similarity_score"):
        assert top.get(field) is not None, _failure_message(
            case, actual_answer=payload.get("solution", ""), chunks=source_chunks, payload=payload
        )


@pytest.fixture()
def deterministic_client(monkeypatch):
    cleanup = install_deterministic_api_overrides(app, CASES, monkeypatch=monkeypatch)
    with TestClient(app) as client:
        yield client
    cleanup()


def test_rag_grade9_fixture_contract():
    assert len(CASES) >= 50
    assert _target_cases("rag/retrieve")
    assert _target_cases("chat/ask")
    assert _target_cases("homework/solve-text")


@pytest.mark.parametrize(
    ("variant", "expected_terms"),
    [
        ("الحموض القوية", ["الحموض", "قوي"]),
        ("الحُمُوضُ القَوِيَّة", ["الحموض", "قوي"]),
        ("احماض قويه", ["حموض", "قوي"]),
        ("H₂O", ["h2o"]),
        ("H2O", ["h2o"]),
        ("التركيز المولي", ["التركز", "المولي"]),
        ("التركز المولي", ["التركز", "المولي"]),
    ],
)
def test_arabic_normalization_and_query_rewrite_terms(variant: str, expected_terms: list[str]):
    combined = f"{normalize_for_assertion(variant)} {normalize_for_assertion(rewrite_query(clean_query(variant)))}"
    missing = [term for term in expected_terms if not contains_term(combined, term)]
    assert not missing, f"variant={variant!r} expected_terms={expected_terms} combined={combined!r}"


def test_arabic_diacritic_and_formula_normalization_equivalence():
    assert normalize_for_assertion("الحموض القوية") == normalize_for_assertion("الحُمُوضُ القَوِيَّة")
    assert normalize_for_assertion("H₂O") == normalize_for_assertion("H2O")


@pytest.mark.parametrize("case", _target_cases("rag/retrieve"), ids=_case_id)
def test_rag_retrieve_grade9_qa_cases(deterministic_client: TestClient, case: dict[str, Any]):
    if not route_exists(app, "/api/v1/rag/retrieve", "POST"):
        pytest.skip("POST /api/v1/rag/retrieve is not implemented")

    response = deterministic_client.post(
        "/api/v1/rag/retrieve",
        json={"query": case["question"], "top_k": 5, "min_similarity": 0.45, "intent": "general"},
    )
    assert response.status_code == 200, _failure_message(case, payload={"status_code": response.status_code})
    payload = response.json()
    chunks = payload.get("chunks", [])

    if case["expected_behavior"] == "out_of_scope":
        assert not chunks, _failure_message(case, chunks=chunks, payload=payload)
        return

    _assert_retrieve_source_metadata(case, chunks, payload)
    retrieved_text = "\n".join(chunk.get("content", "") for chunk in chunks)
    _assert_expected_keywords(case, retrieved_text, chunks=chunks, payload=payload)
    _assert_source_topics(case, retrieved_text, chunks=chunks, payload=payload)
    _assert_no_forbidden_keywords(case, retrieved_text, chunks=chunks, payload=payload)


@pytest.mark.parametrize("case", _target_cases("chat/ask"), ids=_case_id)
def test_chat_ask_grade9_qa_cases(deterministic_client: TestClient, case: dict[str, Any]):
    if not route_exists(app, "/api/v1/chat/ask", "POST"):
        pytest.skip("POST /api/v1/chat/ask is not implemented")

    response = deterministic_client.post(
        "/api/v1/chat/ask",
        json={
            "question": case["question"],
            "preferred_answer_type": "text",
            "answer_scope": "book_only",
            "source_types": ["textbook"],
        },
    )
    assert response.status_code == 200, _failure_message(case, payload={"status_code": response.status_code})
    payload = response.json()
    answer = payload.get("answer", "")

    _assert_no_forbidden_keywords(case, answer, chunks=payload.get("sources", []), payload=payload)

    if case["expected_behavior"] == "out_of_scope":
        assert payload.get("confidence", 1.0) <= 0.25, _failure_message(
            case, actual_answer=answer, chunks=payload.get("sources", []), payload=payload
        )
        assert not payload.get("sources"), _failure_message(case, actual_answer=answer, payload=payload)
        assert contains_term(answer, "لم أجد") or contains_term(answer, "غير كاف"), _failure_message(
            case, actual_answer=answer, payload=payload
        )
        return

    _assert_expected_keywords(case, answer, chunks=payload.get("sources", []), payload=payload)
    _assert_chat_source_metadata(case, payload.get("sources", []), payload)
    assert payload.get("confidence", 0.0) >= float(case["min_confidence"]), _failure_message(
        case, actual_answer=answer, chunks=payload.get("sources", []), payload=payload
    )
    assert payload.get("page_numbers"), _failure_message(
        case, actual_answer=answer, chunks=payload.get("sources", []), payload=payload
    )


@pytest.mark.parametrize("case", _target_cases("homework/solve-text"), ids=_case_id)
def test_homework_solve_text_grade9_qa_cases(deterministic_client: TestClient, case: dict[str, Any]):
    if not route_exists(app, "/api/v1/homework/solve-text", "POST"):
        pytest.skip("POST /api/v1/homework/solve-text is not implemented")

    response = deterministic_client.post("/api/v1/homework/solve-text", json={"problem_text": case["question"]})
    assert response.status_code == 200, _failure_message(case, payload={"status_code": response.status_code})
    payload = response.json()
    solution = payload.get("solution", "")

    _assert_no_forbidden_keywords(case, solution, chunks=payload.get("source_chunks", []), payload=payload)

    if case["expected_behavior"] == "out_of_scope":
        assert payload.get("confidence_score", 1.0) <= 0.25, _failure_message(
            case, actual_answer=solution, chunks=payload.get("source_chunks", []), payload=payload
        )
        assert not payload.get("source_chunks"), _failure_message(case, actual_answer=solution, payload=payload)
        assert contains_term(solution, "لم أجد") or contains_term(solution, "غير كاف"), _failure_message(
            case, actual_answer=solution, payload=payload
        )
        return

    _assert_expected_keywords(case, solution, chunks=payload.get("source_chunks", []), payload=payload)
    _assert_homework_source_metadata(case, payload.get("source_chunks", []), payload)
    assert payload.get("confidence_score", 0.0) >= float(case["min_confidence"]), _failure_message(
        case, actual_answer=solution, chunks=payload.get("source_chunks", []), payload=payload
    )


@pytest.mark.skipif(os.getenv("RUN_RAG_INTEGRATION") != "1", reason="Set RUN_RAG_INTEGRATION=1 for live RAG API tests")
def test_live_rag_retrieve_integration_smoke():
    if not route_exists(app, "/api/v1/rag/retrieve", "POST"):
        pytest.skip("POST /api/v1/rag/retrieve is not implemented")

    app.dependency_overrides[get_current_user_id] = lambda: 101
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rag/retrieve",
                json={"query": "ما هي الحموض؟", "top_k": 5, "min_similarity": 0.45},
            )
        assert response.status_code == 200
        assert "chunks" in response.json()
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
