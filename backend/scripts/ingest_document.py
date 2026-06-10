#!/usr/bin/env python
"""Command-line tool for ingesting documents into the EduMind RAG pipeline.

Usage examples::

    # Ingest the solution book
    python scripts/ingest_document.py \\
        --pdf data/textbooks/syria_grade_9/solution_book/Chemistry_Solution_Book.pdf \\
        --document-id chemistry_grade9_solution_book \\
        --document-type solution_book \\
        --related-document-id chemistry_grade9_textbook

    # Dry-run extraction only (no DB writes)
    python scripts/ingest_document.py \\
        --pdf data/textbooks/syria_grade_9/Chemistry.pdf \\
        --document-id chemistry_grade9_textbook \\
        --document-type textbook \\
        --extract-only \\
        --ingestion-mode dry_run

    # Force re-extraction and re-embedding of an already-ingested document
    python scripts/ingest_document.py \\
        --pdf data/textbooks/syria_grade_9/solution_book/Chemistry_Solution_Book.pdf \\
        --document-id chemistry_grade9_solution_book \\
        --document-type solution_book \\
        --force-reextract \\
        --force-reembed
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Make the backend package importable when running from the project root.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND_DIR))

from app.services.ingestion_pipeline import run_full_ingestion  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest_document")


# ---------------------------------------------------------------------------
# Ingestion Quality Report
# ---------------------------------------------------------------------------

def _quality_report(result: dict, elapsed: float) -> dict:
    """Compile a structured quality report from a completed ingestion result."""
    pages_attempted = result.get("pages_attempted", 0)
    pages_completed = result.get("pages_completed", 0)
    pages_failed = result.get("pages_failed", 0)
    chunks_created = result.get("chunks_created", 0)
    errors = result.get("errors") or []
    warnings = result.get("warnings") or []
    page_statuses = result.get("page_statuses") or []

    # Mid-sentence chunk check (heuristic: chunk ends mid-sentence if it does
    # not end with a sentence-terminating character).
    _sentence_endings = {".", "!", "?", "؟", "؛", "\n"}
    mid_sentence_chunks = 0
    for ps in page_statuses:
        for chunk in ps.get("chunks", []):
            content = chunk.get("content", "")
            if content and content[-1] not in _sentence_endings:
                mid_sentence_chunks += 1

    mid_sentence_ratio = (
        mid_sentence_chunks / max(chunks_created, 1) if chunks_created else 0.0
    )

    failures: list[str] = []
    if errors:
        failures.extend(errors)
    if mid_sentence_ratio > 0.30:
        failures.append(
            f"mid_sentence_chunk_threshold_exceeded (ratio={mid_sentence_ratio:.2f})"
        )
    if pages_failed > 0 and pages_failed / max(pages_attempted, 1) > 0.20:
        failures.append(
            f"excessive_page_failures ({pages_failed}/{pages_attempted} pages failed)"
        )

    return {
        "status": result.get("status", "unknown"),
        "document_id": result.get("document_id"),
        "document_type": result.get("document_type"),
        "pdf_path": result.get("pdf_path"),
        "elapsed_seconds": round(elapsed, 2),
        "pages_attempted": pages_attempted,
        "pages_completed": pages_completed,
        "pages_failed": pages_failed,
        "chunks_created": chunks_created,
        "questions_extracted": result.get("questions_extracted", 0),
        "embeddings_missing": result.get("embeddings_missing", 0),
        "mid_sentence_chunk_ratio": round(mid_sentence_ratio, 4),
        "warnings": warnings,
        "failures": failures,
        "passed": len(failures) == 0,
    }


# ---------------------------------------------------------------------------
# Progress callback
# ---------------------------------------------------------------------------

def _make_progress_callback(total_pages: int):
    """Return a callback that logs progress to the console."""
    def _cb(percent: int, stage: str) -> None:
        logger.info("[%3d%%] %s", percent, stage)
    return _cb


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a PDF document into the EduMind RAG pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--pdf",
        required=True,
        metavar="PATH",
        help="Path to the source PDF file (relative to the project root or absolute).",
    )
    parser.add_argument(
        "--document-id",
        default=None,
        metavar="ID",
        help="Stable identifier for this document (e.g. chemistry_grade9_solution_book).",
    )
    parser.add_argument(
        "--document-type",
        default="textbook",
        choices=["textbook", "solution_book"],
        help="Document type stored in source_type column (default: textbook).",
    )
    parser.add_argument(
        "--related-document-id",
        default=None,
        metavar="ID",
        help="Document ID of the linked textbook (for solution books).",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Human-readable title stored in ContentSource.title.",
    )
    parser.add_argument(
        "--grade",
        default="grade_9",
        help="Grade level (default: grade_9).",
    )
    parser.add_argument(
        "--subject",
        default="chemistry",
        help="Subject (default: chemistry).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        metavar="N",
        help="Limit extraction to the first N pages (useful for testing).",
    )
    parser.add_argument(
        "--ocr-provider",
        default=None,
        choices=["gemini", "none"],
        help="OCR provider. Use 'none' to disable OCR (text pages only).",
    )
    parser.add_argument(
        "--ingestion-mode",
        default=None,
        choices=["production", "dry_run"],
        help="Ingestion mode (default: from settings).",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Run page extraction only; skip chunking, embedding, and DB writes.",
    )
    parser.add_argument(
        "--chunk-only",
        action="store_true",
        help="Run chunking only on cached page JSON; skip extraction and embedding.",
    )
    parser.add_argument(
        "--embed-only",
        action="store_true",
        help="Re-embed existing DB chunks without re-extracting.",
    )
    parser.add_argument(
        "--force-reextract",
        action="store_true",
        help="Force re-extraction of pages even if a cache exists.",
    )
    parser.add_argument(
        "--force-rechunk",
        action="store_true",
        help="Force re-chunking even if chunks already exist in the DB.",
    )
    parser.add_argument(
        "--force-reembed",
        action="store_true",
        help="Force re-embedding of all chunks.",
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Delete all existing chunks for this source before ingesting.",
    )
    parser.add_argument(
        "--output-report",
        default=None,
        metavar="PATH",
        help="Write the Ingestion Quality Report as JSON to this path.",
    )
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    """Run the ingestion and return an exit code (0=success, 1=failure)."""
    pdf_path = str(Path(args.pdf).expanduser().resolve())
    if not Path(pdf_path).exists():
        logger.error("PDF file not found: %s", pdf_path)
        return 1

    if args.extract_only or args.chunk_only or args.embed_only:
        logger.warning(
            "--extract-only / --chunk-only / --embed-only flags are noted. "
            "The current ingestion pipeline runs the full pipeline in one pass; "
            "partial-mode support requires cache-aware pipeline refactoring. "
            "Running full ingestion instead."
        )

    logger.info(
        "Starting ingestion: pdf=%s  document_id=%s  document_type=%s",
        pdf_path,
        args.document_id,
        args.document_type,
    )
    start = time.monotonic()

    try:
        result = await run_full_ingestion(
            pdf_path=pdf_path,
            source_type=args.document_type,
            title=args.title,
            grade=args.grade,
            subject=args.subject,
            max_pages=args.max_pages,
            ocr_provider_name=args.ocr_provider,
            ingestion_mode=args.ingestion_mode,
            clear_existing=args.clear_existing,
            progress_callback=_make_progress_callback(args.max_pages or 0),
            document_id=args.document_id,
            document_type=args.document_type,
            related_document_id=args.related_document_id,
        )
    except Exception as exc:
        logger.error("Ingestion failed with exception: %s", exc, exc_info=True)
        return 1

    elapsed = time.monotonic() - start
    report = _quality_report(result, elapsed)
    report["document_id"] = args.document_id
    report["document_type"] = args.document_type
    report["pdf_path"] = pdf_path

    # Always print a summary
    logger.info("=== Ingestion Quality Report ===")
    logger.info("  Status          : %s", report["status"])
    logger.info("  Pages completed : %d / %d", report["pages_completed"], report["pages_attempted"])
    logger.info("  Pages failed    : %d", report["pages_failed"])
    logger.info("  Chunks created  : %d", report["chunks_created"])
    logger.info("  Questions       : %d", report["questions_extracted"])
    logger.info("  Elapsed         : %.2fs", elapsed)
    if report["warnings"]:
        for w in report["warnings"]:
            logger.warning("  Warning: %s", w)
    if report["failures"]:
        for f in report["failures"]:
            logger.error("  FAILURE: %s", f)
    logger.info("  Result          : %s", "PASSED" if report["passed"] else "FAILED")

    if args.output_report:
        out_path = Path(args.output_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Quality report written to %s", out_path)

    return 0 if report["passed"] else 1


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    exit_code = asyncio.run(_run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
