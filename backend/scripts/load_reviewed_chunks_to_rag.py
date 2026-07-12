#!/usr/bin/env python3
"""Load reviewed textbook/solution chunks into rag_chunks without embedding."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.services.reviewed_ingestion_assets import load_reviewed_chunks_to_rag  # noqa: E402
from scripts.migration_guard import ensure_migrations_applied  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load reviewed JSONL chunks into rag_chunks as pending embeddings."
    )
    parser.add_argument("--clear-existing", action="store_true", help="SQLite test/development only.")
    parser.add_argument("--no-clear-existing", action="store_true", help="Deprecated compatibility flag.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--textbook-only", action="store_true")
    parser.add_argument("--solution-book-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    include_textbook = not args.solution_book_only
    include_solution_book = not args.textbook_only
    ensure_migrations_applied(engine, required_tables=("alembic_version", "content_sources", "rag_chunks"))
    db = SessionLocal()
    try:
        result = load_reviewed_chunks_to_rag(
            db,
            clear_existing=args.clear_existing and not args.no_clear_existing,
            dry_run=args.dry_run,
            include_textbook=include_textbook,
            include_solution_book=include_solution_book,
        )
    finally:
        db.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
