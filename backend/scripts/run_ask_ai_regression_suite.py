#!/usr/bin/env python3
"""Run deterministic Ask AI regression checks and safely gate live execution.

Normal execution mocks all paid providers. Live execution requires
``RUN_ASK_AI_INTEGRATION=1`` and a complete production-like RAG preflight.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
import mimetypes
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.dependencies import get_current_user_id  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.rag_preflight import build_rag_preflight  # noqa: E402
from scripts.ask_ai_regression_harness import (  # noqa: E402
    DATASET_PATH,
    REPORT_JSON_PATH,
    REPORT_MARKDOWN_PATH,
    evaluate_answer,
    load_book_cases,
    repeat_count_from_env,
    run_deterministic_text_suite,
    write_report_files,
)

logging.getLogger("app.main").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


ASK_AI_RAG_INDEX_NOT_READY = "ASK_AI_RAG_INDEX_NOT_READY"
ASK_AI_LIVE_NOT_AUTHORIZED = "ASK_AI_LIVE_NOT_AUTHORIZED"
ASK_AI_AUDIO_PROVIDER_NOT_READY = "ASK_AI_AUDIO_PROVIDER_NOT_READY"
ASK_AI_AUDIO_FIXTURE_NOT_CONFIGURED = "ASK_AI_AUDIO_FIXTURE_NOT_CONFIGURED"
ASK_AI_INTEGRATION_USER_NOT_CONFIGURED = "ASK_AI_INTEGRATION_USER_NOT_CONFIGURED"


def _safe_preflight() -> dict[str, Any]:
    try:
        with SessionLocal() as db:
            return build_rag_preflight(db)
    except Exception as exc:
        return {
            "status": "blocked",
            "can_evaluate": False,
            "database": {"reachable": False, "dialect": "unknown"},
            "provider": {"model": settings.gemini_embedding_model, "configured": False},
            "reviewed_metadata": {
                "version": settings.rag_active_reviewed_metadata_version,
                "ready_for_embedding": False,
            },
            "chunks": {},
            "blocking_issues": [f"DATABASE_PREFLIGHT_FAILED:{type(exc).__name__}"],
            "warnings": [],
        }


def _precondition_summary(preflight: dict[str, Any]) -> dict[str, Any]:
    chunks = preflight.get("chunks") if isinstance(preflight.get("chunks"), dict) else {}
    reviewed = (
        preflight.get("reviewed_metadata")
        if isinstance(preflight.get("reviewed_metadata"), dict)
        else {}
    )
    provider = preflight.get("provider") if isinstance(preflight.get("provider"), dict) else {}
    can_evaluate = preflight.get("can_evaluate") is True
    return {
        "live_status": "ready" if can_evaluate else "blocked",
        "stable_blocker": None if can_evaluate else ASK_AI_RAG_INDEX_NOT_READY,
        "database_reachable": bool((preflight.get("database") or {}).get("reachable")),
        "reviewed_metadata_ready": reviewed.get("ready_for_embedding") is True,
        "reviewed_metadata_version": reviewed.get("version"),
        "embedding_model": provider.get("model") or settings.gemini_embedding_model,
        "gemini_configured": provider.get("configured") is True,
        "elevenlabs_configured": bool(
            settings.audio_enabled
            and settings.elevenlabs_api_key
            and settings.elevenlabs_default_voice_id
        ),
        "media_urls_live_verified": False,
        "database_chunks_total": int(chunks.get("database_chunks_total") or 0),
        "ready_chunks": int(chunks.get("ready_chunks") or 0),
        "needs_review_chunks": int(chunks.get("needs_review_chunks") or 0),
        "blocked_chunks": int(chunks.get("blocked_chunks") or 0),
        "completed_embeddings": int(chunks.get("completed_embeddings") or 0),
        "pending_embeddings": int(chunks.get("pending_embeddings") or 0),
        "processing_embeddings": int(chunks.get("processing_embeddings") or 0),
        "failed_embeddings": int(chunks.get("failed_embeddings") or 0),
        "stale_chunks": int(chunks.get("stale_chunks") or 0),
        "embedding_dimension": (preflight.get("database") or {}).get("embedding_dimension", 768),
        "vector_dimension_valid": bool((preflight.get("database") or {}).get("vector_dimension_valid")),
        "preflight_blocking_issues": list(preflight.get("blocking_issues") or []),
        "preflight_warnings": list(preflight.get("warnings") or []),
    }


def _run_mocked_audio_tests() -> dict[str, Any]:
    env = dict(os.environ)
    env.pop("RUN_ASK_AI_INTEGRATION", None)
    env.pop("RUN_RAG_INTEGRATION", None)
    command = [sys.executable, "-m", "pytest", "tests/test_chat_audio.py", "-q"]
    result = subprocess.run(
        command,
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    passed = result.returncode == 0
    return {
        "matrix_cases": 4,
        "passed_matrix_cases": 4 if passed else 0,
        "pass_rate": 1.0 if passed else 0.0,
        "stt_failures": 0 if passed else 1,
        "tts_failures": 0 if passed else 1,
        "evidence": "tests/test_chat_audio.py",
        "test_command": " ".join(command),
        "test_exit_code": result.returncode,
        "test_output_tail": "\n".join((result.stdout + result.stderr).splitlines()[-20:]),
        "failure_contracts": [
            "empty_request",
            "unsupported_audio_format",
            "oversized_audio",
            "empty_audio",
            "stt_failure_blocks_rag",
            "missing_provider_key",
            "tts_failure_preserves_text",
            "expired_authentication",
        ],
    }


def _deterministic_report(dataset_path: Path) -> dict[str, Any]:
    cases = load_book_cases(dataset_path)
    repeat_count = repeat_count_from_env()
    text_result = run_deterministic_text_suite(cases, repeat_count=repeat_count)
    audio_result = _run_mocked_audio_tests()
    preconditions = _precondition_summary(_safe_preflight())
    deterministic_passed = (
        text_result["pass_rate"] == 1.0
        and text_result["citation_metadata_completeness"] == 1.0
        and text_result["expected_page_hit_rate"] == 1.0
        and text_result["contradiction_count"] == 0
        and text_result["blocked_stale_citation_count"] == 0
        and text_result["out_of_scope_passed"] == text_result["out_of_scope_executions"]
        and audio_result["pass_rate"] == 1.0
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "deterministic",
        "dataset_path": str(dataset_path),
        "preconditions": preconditions,
        "pipeline": {
            "text": "Text -> RAG -> grounded text answer -> optional TTS",
            "audio": "Audio -> ElevenLabs STT -> transcript -> RAG -> grounded text answer -> optional ElevenLabs TTS",
            "audio_bypasses_rag": False,
        },
        "text": text_result,
        "audio": audio_result,
        "total_cases": text_result["book_cases"],
        "total_repetitions": text_result["total_executions"],
        "text_pass_rate": text_result["pass_rate"],
        "audio_pass_rate": audio_result["pass_rate"],
        "citation_completeness": text_result["citation_metadata_completeness"],
        "expected_page_hit_rate": text_result["expected_page_hit_rate"],
        "contradiction_count": text_result["contradiction_count"],
        "blocked_stale_citation_count": text_result["blocked_stale_citation_count"],
        "stt_failures": audio_result["stt_failures"],
        "tts_failures": audio_result["tts_failures"],
        "failed_cases": list(text_result["failed_cases"]),
        "live_external_calls_performed": False,
        "live_note": (
            "Live execution is ready for explicit authorization."
            if preconditions["live_status"] == "ready"
            else f"Live execution stopped before provider calls: {ASK_AI_RAG_INDEX_NOT_READY}."
        ),
        "validation_status": "passed" if deterministic_passed else "failed",
    }


def _representative_live_cases(cases: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_lessons: set[str] = set()
    for case in cases:
        lesson_id = str(case["expected_lesson_id"])
        if lesson_id not in seen_lessons:
            selected.append(case)
            seen_lessons.add(lesson_id)
    for case in cases:
        if case not in selected:
            selected.append(case)
        if len(selected) >= max(limit, len(seen_lessons)):
            break
    return selected[: max(limit, len(seen_lessons))]


def _configured_integration_user_id() -> int | None:
    raw = os.getenv("ASK_AI_INTEGRATION_USER_ID", "").strip()
    if not raw.isdigit():
        return None
    user_id = int(raw)
    try:
        with SessionLocal() as db:
            return user_id if db.scalar(select(User.id).where(User.id == user_id)) else None
    except Exception:
        return None


def _audio_fixture() -> tuple[Path, str] | None:
    raw = os.getenv("ASK_AI_AUDIO_FIXTURE_PATH", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        return None
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if mime_type not in set(settings.allowed_audio_mime_types):
        return None
    return path, mime_type


def _live_prerequisite_blocker(preconditions: dict[str, Any]) -> str | None:
    if os.getenv("RUN_ASK_AI_INTEGRATION") != "1":
        return ASK_AI_LIVE_NOT_AUTHORIZED
    if preconditions["live_status"] != "ready":
        return ASK_AI_RAG_INDEX_NOT_READY
    if not (
        settings.audio_enabled
        and settings.elevenlabs_api_key
        and settings.elevenlabs_default_voice_id
    ):
        return ASK_AI_AUDIO_PROVIDER_NOT_READY
    if _audio_fixture() is None:
        return ASK_AI_AUDIO_FIXTURE_NOT_CONFIGURED
    if _configured_integration_user_id() is None:
        return ASK_AI_INTEGRATION_USER_NOT_CONFIGURED
    return None


def _run_live_text(cases: list[dict[str, Any]], *, user_id: int) -> dict[str, Any]:
    raw_limit = os.getenv("ASK_AI_LIVE_CASE_LIMIT", "10")
    limit = max(1, int(raw_limit))
    selected = _representative_live_cases(cases, limit)
    failures: list[dict[str, Any]] = []
    passed = 0
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    try:
        with TestClient(app) as client:
            for case in selected:
                response = client.post(
                    "/api/v1/chat/ask",
                    json={
                        "question": case["question_ar"],
                        "preferred_answer_type": "text",
                        "answer_scope": "book_only",
                        "source_types": [case["expected_source_type"]],
                    },
                )
                if response.status_code != 200:
                    failures.append({"case_id": case["id"], "reasons": [f"HTTP_{response.status_code}"]})
                    continue
                evaluation = evaluate_answer(case, response.json())
                passed += int(evaluation["passed"])
                if not evaluation["passed"]:
                    failures.append({"case_id": case["id"], "reasons": evaluation["failures"]})
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
    return {
        "cases": len(selected),
        "passed": passed,
        "pass_rate": round(passed / max(len(selected), 1), 4),
        "failed_cases": failures,
    }


def _run_live_audio(case: dict[str, Any], *, user_id: int, fixture: tuple[Path, str]) -> dict[str, Any]:
    path, mime_type = fixture
    expected = {
        "auto": ("text_audio", True),
        "text": ("text", False),
        "audio": ("audio", True),
        "text_audio": ("text_audio", True),
    }
    failures: list[dict[str, Any]] = []
    passed = 0
    stt_failures = 0
    tts_failures = 0
    app.dependency_overrides[get_current_user_id] = lambda: user_id
    try:
        with TestClient(app) as client:
            session_response = client.post("/api/v1/chat/sessions", json={"title": "Ask AI live regression"})
            if session_response.status_code != 201:
                return {
                    "matrix_cases": 4,
                    "passed_matrix_cases": 0,
                    "pass_rate": 0.0,
                    "stt_failures": 4,
                    "tts_failures": 3,
                    "failed_cases": [{"case_id": "audio_session", "reasons": [f"HTTP_{session_response.status_code}"]}],
                }
            session_id = session_response.json()["id"]
            try:
                for requested, (expected_resolved, expects_audio) in expected.items():
                    response = client.post(
                        "/api/v1/chat/messages",
                        data={
                            "conversationId": str(session_id),
                            "requestedReturnType": requested,
                            "language": "ar",
                            "answerScope": "book_only",
                        },
                        files={"audio": (path.name, path.read_bytes(), mime_type)},
                    )
                    reasons: list[str] = []
                    payload = response.json() if response.status_code == 200 else {}
                    if response.status_code != 200:
                        reasons.append(f"HTTP_{response.status_code}")
                    if not str(payload.get("audio_transcript") or "").strip():
                        reasons.append("TRANSCRIPT_MISSING")
                        stt_failures += 1
                    if payload.get("resolved_return_type") != expected_resolved:
                        reasons.append("WRONG_RESOLVED_RETURN_TYPE")
                    if not str(payload.get("answer_text") or "").strip():
                        reasons.append("ANSWER_TEXT_MISSING")
                    if not payload.get("sources"):
                        reasons.append("CITATIONS_MISSING")
                    audio_url = payload.get("answer_audio_url")
                    if expects_audio:
                        if payload.get("audio_status") != "ready" or not audio_url:
                            reasons.append("TTS_NOT_READY")
                            tts_failures += 1
                        elif isinstance(audio_url, str):
                            media_response = client.get(audio_url)
                            if media_response.status_code != 200 or not media_response.content:
                                reasons.append("AUDIO_URL_NOT_PLAYABLE")
                            content_type = media_response.headers.get("content-type", "")
                            if not content_type.startswith("audio/"):
                                reasons.append("AUDIO_MIME_INVALID")
                    elif audio_url:
                        reasons.append("UNEXPECTED_TTS_AUDIO")
                    if reasons:
                        failures.append({"case_id": f"audio_{requested}", "reasons": reasons})
                    else:
                        passed += 1
            finally:
                client.delete(f"/api/v1/chat/sessions/{session_id}")
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
    return {
        "matrix_cases": 4,
        "passed_matrix_cases": passed,
        "pass_rate": round(passed / 4, 4),
        "stt_failures": stt_failures,
        "tts_failures": tts_failures,
        "failed_cases": failures,
    }


def _run_live(report: dict[str, Any], cases: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
    blocker = _live_prerequisite_blocker(report["preconditions"])
    if blocker:
        report["mode"] = "integration"
        report["validation_status"] = "blocked"
        report["preconditions"]["live_status"] = "blocked"
        report["preconditions"]["stable_blocker"] = blocker
        report["live_note"] = f"Live execution stopped before provider calls: {blocker}."
        report["live_external_calls_performed"] = False
        return report, 2

    user_id = _configured_integration_user_id()
    fixture = _audio_fixture()
    assert user_id is not None and fixture is not None
    live_text = _run_live_text(cases, user_id=user_id)
    live_audio = _run_live_audio(cases[0], user_id=user_id, fixture=fixture)
    report["mode"] = "integration"
    report["live_external_calls_performed"] = True
    report["live"] = {"text": live_text, "audio": live_audio}
    report["failed_cases"] = [
        *report.get("failed_cases", []),
        *live_text["failed_cases"],
        *live_audio["failed_cases"],
    ]
    passed = live_text["pass_rate"] >= 0.90 and live_audio["pass_rate"] >= 0.90
    report["validation_status"] = "passed" if passed else "failed"
    report["live_note"] = (
        "Live Ask AI text/audio integration met the 90% acceptance thresholds."
        if passed
        else "Live Ask AI text/audio integration did not meet the 90% acceptance thresholds."
    )
    return report, 0 if passed else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("unit", "integration"), default="unit")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = _deterministic_report(args.dataset)
    exit_code = 0 if report["validation_status"] == "passed" else 1
    if args.mode == "integration":
        report, exit_code = _run_live(report, load_book_cases(args.dataset))
    write_report_files(report)
    print(f"Ask AI regression status: {report['validation_status']}")
    print(f"JSON report: {REPORT_JSON_PATH}")
    print(f"Markdown report: {REPORT_MARKDOWN_PATH}")
    if report["preconditions"].get("stable_blocker"):
        print(f"Live blocker: {report['preconditions']['stable_blocker']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
