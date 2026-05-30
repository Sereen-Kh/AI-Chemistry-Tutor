"""Run the PDF ingestion pipeline from the command line."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, engine
import app.models  # noqa: F401
from app.services.ingestion_pipeline import run_full_ingestion


def progress(value: int, message: str) -> None:
    print(f"{value:3d}% {message}", flush=True)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a chemistry textbook PDF.")
    parser.add_argument("pdf_path")
    parser.add_argument("--chapter-id", type=int, default=None)
    parser.add_argument("--clear-existing", action="store_true")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    result = await run_full_ingestion(
        args.pdf_path,
        chapter_id=args.chapter_id,
        clear_existing=args.clear_existing,
        progress_callback=progress,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
