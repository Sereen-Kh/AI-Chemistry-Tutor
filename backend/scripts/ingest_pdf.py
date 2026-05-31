"""Run the PDF ingestion pipeline from the command line."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.services.ingestion_pipeline import run_full_ingestion  # noqa: E402


def progress(value: int, message: str) -> None:
    print(f"{value:3d}% {message}", flush=True)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a chemistry textbook PDF.")
    parser.add_argument("pdf_path")
    parser.add_argument("--title", default=None)
    parser.add_argument("--source-type", default="textbook")
    parser.add_argument("--grade", default="grade_9")
    parser.add_argument("--subject", default="chemistry")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument(
        "--ocr-provider",
        choices=["gemini", "gemini_vision"],
        default=None,
        help="Vision provider for scanned/mixed pages. Gemini Vision is the only MVP provider.",
    )
    parser.add_argument(
        "--ingestion-mode",
        choices=["production", "dry_run"],
        default=None,
        help="Production blocks completion when required OCR is missing; dry_run records warnings and continues.",
    )
    parser.add_argument(
        "--ocr-required-for-vision",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Require OCR/VLM extraction for NEEDS_VISION and MIXED_VISION pages.",
    )
    parser.add_argument(
        "--allow-partial-ingestion",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Allow a source to complete with warnings when some pages fail.",
    )
    parser.add_argument("--chapter-id", type=int, default=None)
    parser.add_argument("--lesson-id", type=int, default=None)
    parser.add_argument("--topic-id", type=int, default=None)
    parser.add_argument("--clear-existing", action="store_true")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    result = await run_full_ingestion(
        args.pdf_path,
        title=args.title,
        source_type=args.source_type,
        grade=args.grade,
        subject=args.subject,
        year=args.year,
        max_pages=args.max_pages,
        ocr_provider_name=args.ocr_provider,
        ingestion_mode=args.ingestion_mode,
        ocr_required_for_vision=args.ocr_required_for_vision,
        allow_partial_ingestion=args.allow_partial_ingestion,
        chapter_id=args.chapter_id,
        lesson_id=args.lesson_id,
        topic_id=args.topic_id,
        clear_existing=args.clear_existing,
        progress_callback=progress,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
