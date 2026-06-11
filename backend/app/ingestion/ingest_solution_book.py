"""CLI entrypoint for Chemistry solution book ingestion.

Run from ``backend``:

    python -m app.ingestion.ingest_solution_book --mode dry_run
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from app.services.solution_book_ingestion import DEFAULT_PDF_PATH, ingest_solution_book

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_solution_book")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest the Grade 9 Chemistry solution book.")
    parser.add_argument("--file", default=str(DEFAULT_PDF_PATH), help="Path to the solution book PDF.")
    parser.add_argument("--mode", choices=["dry_run", "production"], default="dry_run")
    parser.add_argument("--force-reingest", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--use-ocr", action="store_true", default=True)
    parser.add_argument("--no-ocr", action="store_false", dest="use_ocr")
    parser.add_argument("--use-vision", action="store_true", default=True)
    parser.add_argument("--no-vision", action="store_false", dest="use_vision")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--ocr-provider", choices=["gemini", "gemini_document", "gemini_vision", "none"], default=None)
    parser.add_argument("--document-id", default="chemistry_grade9_solution_book")
    parser.add_argument("--title", default="Chemistry Solution Book - Grade 9")
    parser.add_argument("--output-dir", default="data/processed/solution_book")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    try:
        result = await ingest_solution_book(
            file_path=args.file,
            mode=args.mode,
            force_reingest=args.force_reingest,
            use_ocr=args.use_ocr,
            use_vision=args.use_vision,
            max_pages=args.max_pages,
            ocr_provider_name=args.ocr_provider,
            allow_partial=args.allow_partial,
            document_id=args.document_id,
            title=args.title,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        logger.error("Solution book ingestion failed: %s", exc, exc_info=True)
        return 1

    payload = result.to_dict()
    logger.info("Status: %s", result.status)
    logger.info("Pages: %s, units: %s, chunks: %s", result.pages_total, result.solution_units, result.chunks)
    logger.info("Reports: %s", json.dumps(result.reports, ensure_ascii=False))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not result.errors and result.status not in {"failed"} else 1


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main(sys.argv[1:])
