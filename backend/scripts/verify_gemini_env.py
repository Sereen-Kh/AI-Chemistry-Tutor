#!/usr/bin/env python3
"""Verify Gemini and embedding environment configuration safely."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Any

from hardening_reports import BACKEND_DIR, status_line, write_reports

sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.services.embeddings import embed_query, embedding_provider_status  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify EduMind Gemini environment.")
    parser.add_argument("--live", action="store_true", help="Run a real Gemini embedding API call.")
    parser.add_argument(
        "--ci-safe",
        action="store_true",
        help="Do not fail only because live Gemini secrets are unavailable.",
    )
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    live_requested = bool(args.live)
    api_key_present = bool(settings.effective_gemini_api_key)
    status = embedding_provider_status()
    expected_model = "gemini-embedding-001"
    checks: dict[str, Any] = {
        "gemini_api_key_present": api_key_present,
        "gemini_api_key_redacted": "***present***" if api_key_present else "",
        "gemini_embedding_model": settings.gemini_embedding_model,
        "generation_model": settings.model_name,
        "document_model": settings.gemini_document_model,
        "embedding_provider": settings.embedding_provider,
        "embedding_dimension": settings.embedding_dimension,
        "allow_hash_embeddings": settings.allow_hash_embeddings,
        "allow_local_embeddings": settings.allow_local_embeddings,
        "provider_status": status,
        "live_api_call_requested": live_requested,
        "live_api_call_result": "not_run",
        "embedding_dimension_returned": None,
        "errors": [],
    }

    errors: list[str] = []
    if settings.embedding_provider != "gemini":
        errors.append("EMBEDDING_PROVIDER must be gemini for production.")
    if settings.gemini_embedding_model != expected_model:
        errors.append(f"GEMINI_EMBEDDING_MODEL must be {expected_model}.")
    if settings.embedding_dimension != 768:
        errors.append("EMBEDDING_DIMENSION must be 768.")
    if settings.allow_hash_embeddings:
        errors.append("ALLOW_HASH_EMBEDDINGS must be false in production.")
    if settings.allow_local_embeddings:
        errors.append("ALLOW_LOCAL_EMBEDDINGS must be false in production.")
    if not api_key_present:
        errors.append("GEMINI_API_KEY or GOOGLE_API_KEY is missing.")

    if live_requested and api_key_present:
        try:
            vector = await embed_query("EduMind Gemini environment smoke test")
            checks["embedding_dimension_returned"] = len(vector)
            checks["live_api_call_result"] = "passed" if len(vector) == 768 else "failed"
            if len(vector) != 768:
                errors.append(f"Gemini returned embedding dimension {len(vector)}, expected 768.")
        except Exception as exc:  # pragma: no cover - external service
            checks["live_api_call_result"] = "failed"
            errors.append(f"Live Gemini embedding call failed: {type(exc).__name__}: {exc}")
    elif live_requested and not api_key_present:
        checks["live_api_call_result"] = "skipped_missing_key"
    elif args.ci_safe:
        checks["live_api_call_result"] = "skipped_ci_safe"

    checks["errors"] = errors
    # In CI-safe mode, missing Gemini secrets should be reported but should not
    # fail the pipeline. Unsafe production fallback settings still fail.
    blocking_errors = [
        item for item in errors if not (args.ci_safe and "GEMINI_API_KEY" in item)
    ]
    checks["result"] = "passed" if not blocking_errors else "failed"
    checks["mode"] = "live" if live_requested else "config"
    checks["ci_safe"] = args.ci_safe

    write_reports(
        report_subdir="smoke",
        report_name="gemini_env_report",
        title="Gemini Environment Verification",
        payload=checks,
        sections=[
            (
                "Configuration",
                [
                    status_line("GEMINI_API_KEY present", api_key_present),
                    status_line("Embedding model", settings.gemini_embedding_model),
                    status_line("Generation model", settings.model_name),
                    status_line("Document model", settings.gemini_document_model),
                    status_line("Embedding provider", settings.embedding_provider),
                    status_line("Embedding dimension", settings.embedding_dimension),
                    status_line("ALLOW_HASH_EMBEDDINGS", settings.allow_hash_embeddings),
                    status_line("ALLOW_LOCAL_EMBEDDINGS", settings.allow_local_embeddings),
                ],
            ),
            (
                "Live API Call",
                [
                    status_line("Requested", live_requested),
                    status_line("Result", checks["live_api_call_result"]),
                    status_line("Returned dimension", checks["embedding_dimension_returned"]),
                ],
            ),
            ("Errors", [f"- {item}" for item in errors] if errors else ["- None"]),
        ],
    )
    for item in errors:
        print(f"ERROR: {item}")
    return 0 if checks["result"] == "passed" else 1


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    raise SystemExit(asyncio.run(run()))
