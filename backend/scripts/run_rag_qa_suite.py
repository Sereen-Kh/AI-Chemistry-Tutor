"""Run the deterministic Grade 9 RAG QA suite and export a JSON report.

Default mode is deterministic and does not call Gemini, PostgreSQL, Redis, or
Celery-backed processing. Live integration mode is gated by RUN_RAG_INTEGRATION=1.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.dependencies import get_current_user_id  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services.rag_evaluation import build_evaluation_preconditions  # noqa: E402
from app.services.rag_runtime import active_reviewed_metadata_version, load_json_report  # noqa: E402
from scripts.rag_qa_harness import (  # noqa: E402
    DATASET_PATH,
    REPORT_PATH,
    chunk_previews,
    contains_term,
    install_deterministic_api_overrides,
    load_cases,
    missing_terms,
    present_terms,
    route_exists,
)

logging.getLogger("app.main").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"
GENERATION_FAILURE = "GENERATION_FAILURE"
MISSING_CITATION = "MISSING_CITATION"
INCOMPLETE_CITATION_METADATA = "INCOMPLETE_CITATION_METADATA"
BLOCKED_OR_STALE_CITATION = "BLOCKED_OR_STALE_CITATION"
REVIEWED_VERSION_MISMATCH = "REVIEWED_VERSION_MISMATCH"
UNGROUNDED_ANSWER = "UNGROUNDED_ANSWER"
CONFIDENCE_CONTRACT_FAILURE = "CONFIDENCE_CONTRACT_FAILURE"
OUT_OF_SCOPE_HALLUCINATION = "OUT_OF_SCOPE_HALLUCINATION"


def _failure(code: str, stage: str, detail: str) -> dict[str, str]:
    return {"code": code, "stage": stage, "detail": detail}


def _endpoint_payload(endpoint: str, case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if endpoint == "rag/retrieve":
        return "/api/v1/rag/retrieve", {
            "query": case["question"],
            "top_k": 5,
            "min_similarity": 0.45,
            "intent": "general",
        }
    if endpoint == "chat/ask":
        return "/api/v1/chat/ask", {
            "question": case["question"],
            "preferred_answer_type": "text",
            "answer_scope": "book_only",
            "source_types": ["textbook"],
        }
    if endpoint == "homework/solve-text":
        return "/api/v1/homework/solve-text", {"problem_text": case["question"]}
    raise ValueError(f"Unsupported endpoint target: {endpoint}")


def _source_items(endpoint: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    if endpoint == "rag/retrieve":
        return list(payload.get("chunks") or [])
    if endpoint == "chat/ask":
        return list(payload.get("sources") or [])
    if endpoint == "homework/solve-text":
        return list(payload.get("source_chunks") or [])
    return []


def _answer_text(endpoint: str, payload: dict[str, Any]) -> str:
    if endpoint == "rag/retrieve":
        return "\n".join(str(chunk.get("content") or "") for chunk in payload.get("chunks") or [])
    if endpoint == "chat/ask":
        return str(payload.get("answer") or "")
    if endpoint == "homework/solve-text":
        return str(payload.get("solution") or "")
    return ""


def _confidence(endpoint: str, payload: dict[str, Any]) -> float:
    if endpoint == "rag/retrieve":
        return max((float(chunk.get("similarity_score") or 0.0) for chunk in payload.get("chunks") or []), default=0.0)
    if endpoint == "chat/ask":
        return float(payload.get("confidence") or 0.0)
    if endpoint == "homework/solve-text":
        return float(payload.get("confidence_score") or 0.0)
    return 0.0


def _citation_value(source: dict[str, Any], field: str) -> Any:
    metadata = source.get("curriculum_metadata") if isinstance(source.get("curriculum_metadata"), dict) else {}
    if field == "chunk_id":
        return source.get("id") if source.get("id") is not None else source.get("chunk_id")
    if field == "printed_page_start":
        return (
            source.get("printed_page_start")
            or metadata.get("printed_page_start")
            or source.get("page_number")
        )
    if field == "printed_page_end":
        return (
            source.get("printed_page_end")
            or metadata.get("printed_page_end")
            or source.get("page_number")
        )
    if field == "score":
        return source.get("similarity_score") if source.get("similarity_score") is not None else source.get("score")
    return source.get(field) if source.get(field) is not None else metadata.get(field)


def _citation_issues(sources: list[dict[str, Any]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    required = (
        "chunk_id",
        "source_id",
        "source_type",
        "printed_page_start",
        "printed_page_end",
        "unit_id",
        "lesson_id",
        "score",
        "quality_status",
        "reviewed_metadata_version",
    )
    for source in sources:
        missing = [field for field in required if _citation_value(source, field) in (None, "", [])]
        if missing:
            issues.append(
                _failure(
                    INCOMPLETE_CITATION_METADATA,
                    "citation",
                    f"Missing citation metadata: {missing}",
                )
            )
        quality = str(_citation_value(source, "quality_status") or "")
        metadata = source.get("curriculum_metadata") if isinstance(source.get("curriculum_metadata"), dict) else {}
        if quality == "blocked" or metadata.get("stale") is True:
            issues.append(
                _failure(BLOCKED_OR_STALE_CITATION, "safety", "Blocked or stale citation")
            )
        if _citation_value(source, "reviewed_metadata_version") != active_reviewed_metadata_version():
            issues.append(
                _failure(
                    REVIEWED_VERSION_MISMATCH,
                    "citation",
                    "Reviewed metadata version mismatch",
                )
            )
        if quality == "needs_review" and not source.get("quality_warning"):
            issues.append(
                _failure(
                    INCOMPLETE_CITATION_METADATA,
                    "citation",
                    "needs_review citation missing warning",
                )
            )
    return issues


def _evaluate_endpoint(case: dict[str, Any], endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    answer = _answer_text(endpoint, payload)
    sources = _source_items(endpoint, payload)
    failures: list[dict[str, Any]] = []

    forbidden_hits = present_terms(answer, case["forbidden_keywords"])
    if forbidden_hits:
        failures.append(
            _failure(
                OUT_OF_SCOPE_HALLUCINATION if case["expected_behavior"] == "out_of_scope" else UNGROUNDED_ANSWER,
                "hallucination_guard",
                f"Forbidden terms present: {forbidden_hits}",
            )
        )

    if case["expected_behavior"] == "out_of_scope":
        if sources:
            failures.append(
                _failure(
                    OUT_OF_SCOPE_HALLUCINATION,
                    "hallucination_guard",
                    "Out-of-scope case returned source citations",
                )
            )
        if _confidence(endpoint, payload) > 0.25:
            failures.append(
                _failure(
                    CONFIDENCE_CONTRACT_FAILURE,
                    "confidence",
                    "Out-of-scope confidence is too high",
                )
            )
        if endpoint != "rag/retrieve" and not (contains_term(answer, "لم أجد") or contains_term(answer, "غير كاف")):
            failures.append(
                _failure(
                    OUT_OF_SCOPE_HALLUCINATION,
                    "generation",
                    "Out-of-scope answer did not state insufficient context",
                )
            )
    else:
        if not sources:
            failures.append(_failure(MISSING_CITATION, "citation", "Answerable response has no citation"))
        missing_keywords = missing_terms(answer, case["expected_answer_keywords"])
        if missing_keywords:
            failures.append(
                _failure(
                    GENERATION_FAILURE,
                    "generation",
                    f"Missing expected keywords: {missing_keywords}",
                )
            )
        missing_topics = missing_terms(answer, case["expected_source_topics"])
        if endpoint == "rag/retrieve" and missing_topics:
            failures.append(
                _failure(
                    RETRIEVAL_FAILURE,
                    "retrieval",
                    f"Missing expected source topics: {missing_topics}",
                )
            )
        failures.extend(_citation_issues(sources))
        if _confidence(endpoint, payload) < float(case["min_confidence"]):
            failures.append(
                _failure(
                    CONFIDENCE_CONTRACT_FAILURE,
                    "confidence",
                    "Confidence below expected minimum",
                )
            )

    citation_issue_sources = sum(
        bool(_citation_issues([source])) for source in sources
    )

    return {
        "case_id": case["id"],
        "category": case["category"],
        "endpoint": endpoint,
        "question": case["question"],
        "expected_behavior": case["expected_behavior"],
        "passed": not failures,
        "failures": failures,
        "failure_codes": sorted({failure["code"] for failure in failures}),
        "confidence": _confidence(endpoint, payload),
        "citation_count": len(sources),
        "complete_citation_count": max(0, len(sources) - citation_issue_sources),
        "expected_answer_keywords": case["expected_answer_keywords"],
        "actual_answer": answer[:1000],
        "retrieved_chunk_previews": chunk_previews(sources),
    }


def run_suite(cases: list[dict[str, Any]], *, mode: str) -> dict[str, Any]:
    cleanup = None
    if mode == "unit":
        cleanup = install_deterministic_api_overrides(app, cases)
    else:
        if os.getenv("RUN_RAG_INTEGRATION") != "1":
            raise SystemExit("Set RUN_RAG_INTEGRATION=1 to run integration mode.")
        app.dependency_overrides[get_current_user_id] = lambda: 101

    results: list[dict[str, Any]] = []
    try:
        with TestClient(app) as client:
            for case in cases:
                for endpoint in case["endpoint_targets"]:
                    path, body = _endpoint_payload(endpoint, case)
                    if not route_exists(app, path, "POST"):
                        results.append(
                            {
                                "case_id": case["id"],
                                "endpoint": endpoint,
                                "question": case["question"],
                                "passed": False,
                                "skipped": True,
                                "failures": [{"stage": "endpoint", "detail": f"POST {path} is not implemented"}],
                            }
                        )
                        continue
                    response = client.post(path, json=body)
                    if response.status_code != 200:
                        results.append(
                            {
                                "case_id": case["id"],
                                "endpoint": endpoint,
                                "question": case["question"],
                                "passed": False,
                                "failures": [
                                    {
                                        "stage": "http",
                                        "detail": f"Expected 200, got {response.status_code}: {response.text[:500]}",
                                    }
                                ],
                            }
                        )
                        continue
                    results.append(_evaluate_endpoint(case, endpoint, response.json()))
    finally:
        if cleanup:
            cleanup()
        elif mode == "integration":
            app.dependency_overrides.pop(get_current_user_id, None)

    total = len(results)
    passed = sum(1 for result in results if result.get("passed"))
    failures_by_stage: dict[str, int] = {}
    for result in results:
        for failure in result.get("failures", []):
            stage = str(failure.get("stage") or "unknown")
            failures_by_stage[stage] = failures_by_stage.get(stage, 0) + 1

    answerable_results = [result for result in results if result.get("expected_behavior") == "answerable"]
    out_of_scope_results = [result for result in results if result.get("expected_behavior") == "out_of_scope"]
    citation_denominator = sum(max(1, int(result.get("citation_count") or 0)) for result in answerable_results)
    complete_citations = sum(int(result.get("complete_citation_count") or 0) for result in answerable_results)
    safety_failures = sum(
        1
        for result in results
        for failure in result.get("failures", [])
        if failure.get("code") in {OUT_OF_SCOPE_HALLUCINATION, BLOCKED_OR_STALE_CITATION}
    )
    blocked_stale_citations = sum(
        1
        for result in results
        for failure in result.get("failures", [])
        if failure.get("code") == BLOCKED_OR_STALE_CITATION
    )
    out_of_scope_passed = sum(result.get("passed") is True for result in out_of_scope_results)
    pass_rate = round(passed / total, 4) if total else 0.0
    citation_completeness = round(complete_citations / max(citation_denominator, 1), 4)
    out_of_scope_safety = round(out_of_scope_passed / max(len(out_of_scope_results), 1), 4)
    thresholds = {
        "overall_pass_rate": 1.0 if mode == "unit" else 0.90,
        "safety_hallucination_failures": 0,
        "blocked_stale_citations": 0,
        "citation_metadata_completeness": 1.0,
        "out_of_scope_safety_behavior": 1.0,
    }
    threshold_failures: list[str] = []
    if pass_rate < thresholds["overall_pass_rate"]:
        threshold_failures.append("overall_pass_rate_below_threshold")
    if safety_failures:
        threshold_failures.append("safety_hallucination_failures_above_threshold")
    if blocked_stale_citations:
        threshold_failures.append("blocked_stale_citations_above_threshold")
    if citation_completeness < 1.0:
        threshold_failures.append("citation_metadata_completeness_below_threshold")
    if out_of_scope_safety < 1.0:
        threshold_failures.append("out_of_scope_safety_behavior_below_threshold")

    endpoint_metrics: dict[str, dict[str, int]] = {}
    for result in results:
        endpoint = str(result.get("endpoint") or "unknown")
        metric = endpoint_metrics.setdefault(endpoint, {"total": 0, "passed": 0, "failed": 0})
        metric["total"] += 1
        metric["passed" if result.get("passed") else "failed"] += 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not threshold_failures else "failed",
        "mode": mode,
        "dataset": str(DATASET_PATH),
        "reviewed_metadata_version": active_reviewed_metadata_version(),
        "embedding_model": settings.gemini_embedding_model,
        "preconditions": {
            "mode": mode,
            "live_integration_authorized": mode == "integration" and os.getenv("RUN_RAG_INTEGRATION") == "1",
        },
        "metrics": {
            "overall_pass_rate": pass_rate,
            "safety_hallucination_failures": safety_failures,
            "blocked_stale_citations": blocked_stale_citations,
            "citation_metadata_completeness": citation_completeness,
            "out_of_scope_safety_behavior": out_of_scope_safety,
            "by_endpoint": endpoint_metrics,
            "failures_by_stage": failures_by_stage,
            "thresholds": thresholds,
        },
        "threshold_failures": threshold_failures,
        "failed_cases": [result for result in results if not result.get("passed")],
        "summary": {
            "total_checks": total,
            "passed_checks": passed,
            "failed_checks": total - passed,
            "pass_rate": pass_rate,
            "failures_by_stage": failures_by_stage,
        },
        "results": results,
    }


async def _integration_preconditions() -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        preconditions = await build_evaluation_preconditions(db)
    evaluation = load_json_report(settings.rag_evaluation_report_path)
    issues = list(preconditions.get("blocking_issues") or [])
    if not evaluation or evaluation.get("status") != "passed":
        issues.append("RAG_EVALUATION_GATE_NOT_PASSED")
    elif (
        evaluation.get("reviewed_metadata_version") != active_reviewed_metadata_version()
        or evaluation.get("embedding_model") != settings.gemini_embedding_model
    ):
        issues.append("RAG_EVALUATION_REPORT_VERSION_MISMATCH")
    return {**preconditions, "blocking_issues": list(dict.fromkeys(issues)), "ready": not issues}


def _write_markdown(report: dict[str, Any], output_path: Path) -> Path:
    markdown_path = output_path.with_suffix(".md")
    metrics = report.get("metrics") or {}
    lines = [
        "# Grade 9 Student-Flow RAG QA",
        "",
        f"Status: `{report.get('status')}`",
        f"Mode: `{report.get('mode')}`",
        f"Reviewed metadata: `{report.get('reviewed_metadata_version')}`",
        f"Embedding model: `{report.get('embedding_model')}`",
        "",
        "## Metrics",
        "",
    ]
    lines.extend(f"- `{key}`: `{value}`" for key, value in metrics.items())
    lines.extend(["", "## Threshold Failures", ""])
    lines.extend(f"- `{item}`" for item in report.get("threshold_failures") or [])
    if not report.get("threshold_failures"):
        lines.append("- None")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return markdown_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EduMind Grade 9 RAG QA suite.")
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--mode", choices=["unit", "integration"], default="unit")
    args = parser.parse_args()

    cases = load_cases(Path(args.dataset).expanduser().resolve())
    if args.mode == "integration":
        if os.getenv("RUN_RAG_INTEGRATION") != "1":
            raise SystemExit("Set RUN_RAG_INTEGRATION=1 to run integration mode.")
        preconditions = asyncio.run(_integration_preconditions())
        if not preconditions["ready"]:
            blocked_report = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "status": "blocked",
                "mode": args.mode,
                "dataset": str(args.dataset),
                "reviewed_metadata_version": active_reviewed_metadata_version(),
                "embedding_model": settings.gemini_embedding_model,
                "preconditions": preconditions,
                "metrics": {},
                "threshold_failures": preconditions["blocking_issues"],
                "failed_cases": [],
                "summary": {"total_checks": 0, "passed_checks": 0, "failed_checks": 0, "pass_rate": 0.0},
                "results": [],
            }
            output_path = Path(args.output).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            blocked_report["report_json_path"] = str(output_path)
            blocked_report["report_markdown_path"] = str(output_path.with_suffix(".md"))
            output_path.write_text(json.dumps(blocked_report, ensure_ascii=False, indent=2), encoding="utf-8")
            _write_markdown(blocked_report, output_path)
            print(json.dumps(blocked_report["preconditions"], ensure_ascii=False, indent=2))
            raise SystemExit(1)
    report = run_suite(cases, mode=args.mode)

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report["report_json_path"] = str(output_path)
    report["report_markdown_path"] = str(output_path.with_suffix(".md"))
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path = _write_markdown(report, output_path)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote RAG QA report to {output_path}")
    print(f"Wrote RAG QA Markdown report to {markdown_path}")

    if report["threshold_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
