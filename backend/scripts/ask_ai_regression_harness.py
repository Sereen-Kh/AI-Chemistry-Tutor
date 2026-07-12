"""Deterministic helpers for the reviewed Ask AI regression suite."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from scripts.rag_qa_harness import (
    REVIEWED_METADATA_VERSION,
    contains_term,
    install_deterministic_api_overrides,
    normalize_for_assertion,
)


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
DATASET_PATH = BACKEND_DIR / "tests" / "fixtures" / "ask_ai_grade9_book_questions.json"
REPORT_DIR = REPO_ROOT / "reports" / "ask_ai_regression"
REPORT_JSON_PATH = REPORT_DIR / "ask_ai_regression_report.json"
REPORT_MARKDOWN_PATH = REPORT_DIR / "ask_ai_regression_report.md"
DEFAULT_REPEAT_COUNT = 3

REQUIRED_FIELDS = {
    "id",
    "question_ar",
    "paraphrases_ar",
    "expected_concepts",
    "expected_unit_id",
    "expected_lesson_id",
    "expected_printed_pages",
    "expected_source_type",
    "answerable_from_book",
}

OUT_OF_SCOPE_QUESTION = "ما هي عاصمة كوكب المريخ؟"


def repeat_count_from_env() -> int:
    raw = os.getenv("ASK_AI_REPEAT_COUNT", str(DEFAULT_REPEAT_COUNT))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("ASK_AI_REPEAT_COUNT must be an integer") from exc
    if value < 1:
        raise ValueError("ASK_AI_REPEAT_COUNT must be at least 1")
    return value


def load_book_cases(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Ask AI dataset must be a non-empty JSON list: {path}")

    seen_ids: set[str] = set()
    for index, case in enumerate(payload, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Ask AI case #{index} must be an object")
        missing = REQUIRED_FIELDS - set(case)
        if missing:
            raise ValueError(f"Ask AI case {case.get('id', index)} is missing {sorted(missing)}")
        case_id = str(case["id"])
        if not case_id or case_id in seen_ids:
            raise ValueError(f"Duplicate or empty Ask AI case id: {case_id!r}")
        seen_ids.add(case_id)
        if not str(case["question_ar"]).strip():
            raise ValueError(f"Ask AI case {case_id} has an empty question")
        if not isinstance(case["paraphrases_ar"], list) or not case["paraphrases_ar"]:
            raise ValueError(f"Ask AI case {case_id} must include paraphrases")
        if not isinstance(case["expected_concepts"], list) or not case["expected_concepts"]:
            raise ValueError(f"Ask AI case {case_id} must include expected concepts")
        if not isinstance(case["expected_printed_pages"], list) or not case["expected_printed_pages"]:
            raise ValueError(f"Ask AI case {case_id} must include expected printed pages")
        if not all(isinstance(page, int) and page > 0 for page in case["expected_printed_pages"]):
            raise ValueError(f"Ask AI case {case_id} has invalid printed pages")
        if case["expected_source_type"] not in {"textbook", "solution_book"}:
            raise ValueError(f"Ask AI case {case_id} has an invalid source type")
        if case["answerable_from_book"] is not True:
            raise ValueError(f"Reviewed book case {case_id} must be answerable_from_book=true")
    return payload


def question_variants(case: dict[str, Any]) -> list[str]:
    variants = [str(case["question_ar"]).strip()]
    variants.extend(str(item).strip() for item in case["paraphrases_ar"] if str(item).strip())
    return list(dict.fromkeys(variants))


def to_harness_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Adapt reviewed cases to the existing deterministic RAG QA harness."""

    adapted: list[dict[str, Any]] = []
    for case in cases:
        for variant_index, question in enumerate(question_variants(case)):
            adapted.append(
                {
                    "id": f"{case['id']}__variant_{variant_index}",
                    "source_case_id": case["id"],
                    "category": "reviewed_book",
                    "question": question,
                    "expected_answer_keywords": list(case["expected_concepts"]),
                    "forbidden_keywords": [],
                    "expected_source_topics": list(case["expected_concepts"]),
                    "min_confidence": 0.80,
                    "expected_behavior": "answerable",
                    "endpoint_targets": ["chat/ask"],
                    "expected_unit_id": case["expected_unit_id"],
                    "expected_lesson_id": case["expected_lesson_id"],
                    "expected_printed_pages": list(case["expected_printed_pages"]),
                    "expected_source_type": case["expected_source_type"],
                    "expected_quality_status": "ready",
                }
            )
    adapted.append(
        {
            "id": "ask_ai_out_of_scope",
            "source_case_id": "ask_ai_out_of_scope",
            "category": "out_of_scope",
            "question": OUT_OF_SCOPE_QUESTION,
            "expected_answer_keywords": [],
            "forbidden_keywords": [],
            "expected_source_topics": [],
            "min_confidence": 0.0,
            "expected_behavior": "out_of_scope",
            "endpoint_targets": ["chat/ask"],
        }
    )
    return adapted


def _citation_value(source: dict[str, Any], field: str) -> Any:
    metadata = source.get("curriculum_metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    if field == "score":
        return source.get("similarity_score") if source.get("similarity_score") is not None else source.get("score")
    if field == "printed_page_start":
        return source.get("printed_page_start") or metadata.get("printed_page_start") or source.get("page_number")
    if field == "printed_page_end":
        return source.get("printed_page_end") or metadata.get("printed_page_end") or source.get("page_number")
    return source.get(field) if source.get(field) is not None else metadata.get(field)


def citation_signature(source: dict[str, Any]) -> tuple[Any, ...]:
    return (
        source.get("chunk_id"),
        source.get("source_id"),
        _citation_value(source, "source_type"),
        _citation_value(source, "printed_page_start"),
        _citation_value(source, "unit_id"),
        _citation_value(source, "lesson_id"),
        _citation_value(source, "reviewed_metadata_version"),
    )


def evaluate_answer(case: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    answer = str(payload.get("answer") or "").strip()
    sources = list(payload.get("sources") or [])
    if not answer:
        failures.append("EMPTY_ANSWER")
    if not re.search(r"[\u0621-\u064A]", answer):
        failures.append("ANSWER_NOT_ARABIC")
    for concept in case["expected_concepts"]:
        if not contains_term(answer, str(concept)):
            failures.append(f"EXPECTED_CONCEPT_MISSING:{concept}")
    if not sources:
        failures.append("CITATIONS_MISSING")

    expected_pages = set(int(page) for page in case["expected_printed_pages"])
    page_hit = False
    citation_complete = True
    blocked_stale_count = 0
    for source in sources:
        required = (
            "chunk_id",
            "source_id",
            "source_type",
            "printed_page_start",
            "printed_page_end",
            "unit_id",
            "lesson_id",
            "quality_status",
            "reviewed_metadata_version",
            "score",
        )
        missing = [field for field in required if _citation_value(source, field) in (None, "", [])]
        if missing:
            citation_complete = False
            failures.append(f"CITATION_METADATA_MISSING:{','.join(missing)}")
        page_start = _citation_value(source, "printed_page_start")
        page_end = _citation_value(source, "printed_page_end")
        if isinstance(page_start, int) and isinstance(page_end, int):
            page_hit = page_hit or bool(expected_pages.intersection(range(page_start, page_end + 1)))
        if _citation_value(source, "source_type") != case["expected_source_type"]:
            failures.append("WRONG_SOURCE_TYPE")
        if _citation_value(source, "unit_id") != case["expected_unit_id"]:
            failures.append("WRONG_UNIT_ID")
        if _citation_value(source, "lesson_id") != case["expected_lesson_id"]:
            failures.append("WRONG_LESSON_ID")
        quality = _citation_value(source, "quality_status")
        metadata = source.get("curriculum_metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        if quality == "blocked" or metadata.get("stale") is True:
            blocked_stale_count += 1
            failures.append("BLOCKED_OR_STALE_CITATION")
        if quality == "needs_review" and not source.get("quality_warning"):
            failures.append("NEEDS_REVIEW_WARNING_MISSING")
        if _citation_value(source, "reviewed_metadata_version") != REVIEWED_METADATA_VERSION:
            failures.append("REVIEWED_METADATA_VERSION_MISMATCH")
    if sources and not page_hit:
        failures.append("EXPECTED_PRINTED_PAGE_MISSED")

    return {
        "passed": not failures,
        "failures": list(dict.fromkeys(failures)),
        "answer": answer,
        "sources": sources,
        "citation_complete": citation_complete and bool(sources),
        "expected_page_hit": page_hit,
        "blocked_stale_count": blocked_stale_count,
    }


def run_deterministic_text_suite(
    cases: list[dict[str, Any]],
    *,
    repeat_count: int,
) -> dict[str, Any]:
    harness_cases = to_harness_cases(cases)
    cleanup = install_deterministic_api_overrides(app, harness_cases)
    failed_cases: list[dict[str, Any]] = []
    total_executions = 0
    passed_executions = 0
    citation_complete_executions = 0
    page_hit_executions = 0
    blocked_stale_citations = 0
    contradiction_count = 0
    unstable_source_count = 0

    try:
        with TestClient(app) as client:
            for case in cases:
                answers: set[str] = set()
                source_signatures: set[tuple[Any, ...]] = set()
                for question in question_variants(case):
                    for repetition in range(1, repeat_count + 1):
                        total_executions += 1
                        response = client.post(
                            "/api/v1/chat/ask",
                            json={
                                "question": question,
                                "preferred_answer_type": "text",
                                "answer_scope": "book_only",
                                "source_types": [case["expected_source_type"]],
                            },
                        )
                        if response.status_code != 200:
                            failed_cases.append(
                                {
                                    "case_id": case["id"],
                                    "question": question,
                                    "repetition": repetition,
                                    "reasons": [f"HTTP_{response.status_code}"],
                                }
                            )
                            continue
                        evaluation = evaluate_answer(case, response.json())
                        blocked_stale_citations += int(evaluation["blocked_stale_count"])
                        citation_complete_executions += int(evaluation["citation_complete"])
                        page_hit_executions += int(evaluation["expected_page_hit"])
                        if evaluation["passed"]:
                            passed_executions += 1
                        else:
                            failed_cases.append(
                                {
                                    "case_id": case["id"],
                                    "question": question,
                                    "repetition": repetition,
                                    "reasons": evaluation["failures"],
                                }
                            )
                        answers.add(normalize_for_assertion(evaluation["answer"]))
                        if evaluation["sources"]:
                            source_signatures.add(citation_signature(evaluation["sources"][0]))
                if len(answers) > 1:
                    contradiction_count += 1
                    failed_cases.append(
                        {"case_id": case["id"], "reasons": ["ANSWER_CHANGED_ACROSS_PARAPHRASES_OR_REPEATS"]}
                    )
                if len(source_signatures) > 1:
                    unstable_source_count += 1
                    failed_cases.append(
                        {"case_id": case["id"], "reasons": ["TOP_SOURCE_IDENTITY_UNSTABLE"]}
                    )

            out_of_scope_passed = 0
            for repetition in range(1, repeat_count + 1):
                response = client.post(
                    "/api/v1/chat/ask",
                    json={
                        "question": OUT_OF_SCOPE_QUESTION,
                        "preferred_answer_type": "text",
                        "answer_scope": "book_only",
                        "source_types": ["textbook"],
                    },
                )
                payload = response.json() if response.status_code == 200 else {}
                answer = str(payload.get("answer") or "")
                passed = (
                    response.status_code == 200
                    and not payload.get("sources")
                    and float(payload.get("confidence") or 0.0) <= 0.25
                    and (contains_term(answer, "لم أجد") or contains_term(answer, "غير كاف"))
                )
                out_of_scope_passed += int(passed)
                if not passed:
                    failed_cases.append(
                        {
                            "case_id": "ask_ai_out_of_scope",
                            "repetition": repetition,
                            "reasons": ["OUT_OF_SCOPE_SAFETY_FAILED"],
                        }
                    )
    finally:
        cleanup()

    return {
        "book_cases": len(cases),
        "question_variants": sum(len(question_variants(case)) for case in cases),
        "repeat_count": repeat_count,
        "total_executions": total_executions,
        "passed_executions": passed_executions,
        "pass_rate": round(passed_executions / max(total_executions, 1), 4),
        "citation_metadata_completeness": round(
            citation_complete_executions / max(total_executions, 1), 4
        ),
        "expected_page_hit_rate": round(page_hit_executions / max(total_executions, 1), 4),
        "contradiction_count": contradiction_count,
        "unstable_source_count": unstable_source_count,
        "blocked_stale_citation_count": blocked_stale_citations,
        "out_of_scope_executions": repeat_count,
        "out_of_scope_passed": out_of_scope_passed,
        "failed_cases": failed_cases,
    }


def write_report_files(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    preconditions = report.get("preconditions") or {}
    text_metrics = report.get("text") or {}
    audio_metrics = report.get("audio") or {}
    failed_cases = list(report.get("failed_cases") or [])
    lines = [
        "# Ask AI Regression Report",
        "",
        f"- Validation status: **{report.get('validation_status', 'unknown')}**",
        f"- Generated at: `{report.get('generated_at', 'unknown')}`",
        f"- Live external calls performed: **{str(report.get('live_external_calls_performed', False)).lower()}**",
        "",
        "## Preconditions",
        "",
        f"- Live status: `{preconditions.get('live_status', 'not_checked')}`",
        f"- Stable blocker: `{preconditions.get('stable_blocker') or 'none'}`",
        f"- Database chunks: `{preconditions.get('database_chunks_total', 0)}`",
        f"- Ready / needs review / blocked: `{preconditions.get('ready_chunks', 0)}` / "
        f"`{preconditions.get('needs_review_chunks', 0)}` / `{preconditions.get('blocked_chunks', 0)}`",
        f"- Completed / pending / failed embeddings: `{preconditions.get('completed_embeddings', 0)}` / "
        f"`{preconditions.get('pending_embeddings', 0)}` / `{preconditions.get('failed_embeddings', 0)}`",
        f"- Embedding model: `{preconditions.get('embedding_model') or 'unknown'}`",
        f"- Reviewed metadata version: `{preconditions.get('reviewed_metadata_version') or 'unknown'}`",
        f"- Gemini configured: `{str(preconditions.get('gemini_configured', False)).lower()}`",
        f"- ElevenLabs configured: `{str(preconditions.get('elevenlabs_configured', False)).lower()}`",
        f"- Live media URLs verified: `{str(preconditions.get('media_urls_live_verified', False)).lower()}`",
        "",
        "## Pipeline Under Test",
        "",
        "- Text: `Text -> RAG -> grounded text answer -> optional TTS`",
        "- Audio: `Audio -> STT transcript -> RAG -> grounded text answer -> optional TTS`",
        "- Audio never bypasses RAG.",
        "",
        "## Deterministic Text",
        "",
        f"- Book cases: `{text_metrics.get('book_cases', 0)}`",
        f"- Question variants: `{text_metrics.get('question_variants', 0)}`",
        f"- Repetitions per variant: `{text_metrics.get('repeat_count', 0)}`",
        f"- Executions: `{text_metrics.get('total_executions', 0)}`",
        f"- Pass rate: `{text_metrics.get('pass_rate', 0):.2%}`",
        f"- Citation metadata completeness: `{text_metrics.get('citation_metadata_completeness', 0):.2%}`",
        f"- Expected-page hit rate: `{text_metrics.get('expected_page_hit_rate', 0):.2%}`",
        f"- Contradictions: `{text_metrics.get('contradiction_count', 0)}`",
        f"- Blocked/stale citations: `{text_metrics.get('blocked_stale_citation_count', 0)}`",
        "",
        "## Deterministic Audio",
        "",
        f"- Matrix cases: `{audio_metrics.get('matrix_cases', 0)}`",
        f"- Pass rate: `{audio_metrics.get('pass_rate', 0):.2%}`",
        f"- STT failures: `{audio_metrics.get('stt_failures', 0)}`",
        f"- TTS failures: `{audio_metrics.get('tts_failures', 0)}`",
        f"- Evidence: `{audio_metrics.get('evidence', 'not run')}`",
        "",
        "## Failed Cases",
        "",
    ]
    if failed_cases:
        for item in failed_cases[:100]:
            lines.append(f"- `{item.get('case_id', 'unknown')}`: {', '.join(item.get('reasons') or [])}")
    else:
        lines.append("- None in deterministic execution.")
    lines.extend(
        [
            "",
            "## Live Execution",
            "",
            str(report.get("live_note") or "Live integration was not executed."),
            "",
        ]
    )
    REPORT_MARKDOWN_PATH.write_text("\n".join(lines), encoding="utf-8")
