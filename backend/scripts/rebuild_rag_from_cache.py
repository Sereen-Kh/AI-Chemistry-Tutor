"""Rebuild RAG chunks from cached page JSON files.

Run from the backend directory:
    EMBEDDING_PROVIDER=local_hash .venv/bin/python -m scripts.rebuild_rag_from_cache

Use ``EMBEDDING_PROVIDER=local_multilingual`` after installing backend
requirements if you want semantic local embeddings instead of lightweight
hash embeddings.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.services.rag_rebuild import default_chemistry_cache_dir, rebuild_rag_chunks_from_cached_pages  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild RAG chunks from cached page_NNN.json files.")
    parser.add_argument("--cache-dir", default=str(default_chemistry_cache_dir()))
    parser.add_argument("--title", default="syria_grade_9_chemistry")
    parser.add_argument("--source-type", default="textbook")
    parser.add_argument("--grade", default="grade_9")
    parser.add_argument("--subject", default="chemistry")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--file-path", default=None)
    parser.add_argument("--chapter-id", type=int, default=None)
    parser.add_argument("--lesson-id", type=int, default=None)
    parser.add_argument("--topic-id", type=int, default=None)
    parser.add_argument("--no-clear-existing", action="store_true")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = await rebuild_rag_chunks_from_cached_pages(
            db,
            cache_dir=args.cache_dir,
            title=args.title,
            source_type=args.source_type,
            grade=args.grade,
            subject=args.subject,
            year=args.year,
            file_path=args.file_path,
            chapter_id=args.chapter_id,
            lesson_id=args.lesson_id,
            topic_id=args.topic_id,
            clear_existing=not args.no_clear_existing,
        )
    finally:
        db.close()

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
