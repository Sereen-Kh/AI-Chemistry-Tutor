"""Run the deterministic Grade 9 RAG QA suite and export a JSON report.

Default mode is deterministic and does not call Gemini, PostgreSQL, Redis, or
Celery-backed processing. Live integration mode is gated by RUN_RAG_INTEGRATION=1.
"""

from __future__ import annotations

import argparse
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
from app.main import app  # noqa: E402
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


def _has_required_source_metadata(endpoint: str, sources: list[dict[str, Any]]) -> bool:
    if not sources:
        return False
    fields = ("source_id", "page_number", "similarity_score")
    id_field = "id" if endpoint == "rag/retrieve" else "chunk_id"
    top = sources[0]
    return top.get(id_field) is not None and all(top.get(field) is not None for field in fields)


def _evaluate_endpoint(case: dict[str, Any], endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    answer = _answer_text(endpoint, payload)
    sources = _source_items(endpoint, payload)
    failures: list[dict[str, Any]] = []

    forbidden_hits = present_terms(answer, case["forbidden_keywords"])
    if forbidden_hits:
        failures.append({"stage": "hallucination_guard", "detail": f"Forbidden terms present: {forbidden_hits}"})

    if case["expected_behavior"] == "out_of_scope":
        if sources:
            failures.append({"stage": "hallucination_guard", "detail": "Out-of-scope case returned source citations"})
        if _confidence(endpoint, payload) > 0.25:
            failures.append({"stage": "confidence", "detail": "Out-of-scope confidence is too high"})
        if endpoint != "rag/retrieve" and not (contains_term(answer, "لم أجد") or contains_term(answer, "غير كاف")):
            failures.append({"stage": "generation", "detail": "Out-of-scope answer did not state insufficient context"})
    else:
        missing_keywords = missing_terms(answer, case["expected_answer_keywords"])
        if missing_keywords:
            failures.append({"stage": "generation", "detail": f"Missing expected keywords: {missing_keywords}"})
        missing_topics = missing_terms(answer, case["expected_source_topics"])
        if endpoint == "rag/retrieve" and missing_topics:
            failures.append({"stage": "retrieval", "detail": f"Missing expected source topics: {missing_topics}"})
        if not _has_required_source_metadata(endpoint, sources):
            failures.append({"stage": "citation", "detail": "Missing chunk/source/page/score metadata"})
        if _confidence(endpoint, payload) < float(case["min_confidence"]):
            failures.append({"stage": "confidence", "detail": "Confidence below expected minimum"})

    return {
        "case_id": case["id"],
        "category": case["category"],
        "endpoint": endpoint,
        "question": case["question"],
        "expected_behavior": case["expected_behavior"],
        "passed": not failures,
        "failures": failures,
        "confidence": _confidence(endpoint, payload),
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

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "dataset": str(DATASET_PATH),
        "summary": {
            "total_checks": total,
            "passed_checks": passed,
            "failed_checks": total - passed,
            "pass_rate": round(passed / total, 4) if total else 0.0,
            "failures_by_stage": failures_by_stage,
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EduMind Grade 9 RAG QA suite.")
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    parser.add_argument("--output", default=str(REPORT_PATH))
    parser.add_argument("--mode", choices=["unit", "integration"], default="unit")
    args = parser.parse_args()

    cases = load_cases(Path(args.dataset).expanduser().resolve())
    report = run_suite(cases, mode=args.mode)

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"Wrote RAG QA report to {output_path}")

    if report["summary"]["failed_checks"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
