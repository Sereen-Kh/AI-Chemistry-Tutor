"""Rebuild rag_chunks from cached page extraction JSON files."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401
from app.models.textbook import ContentSource, RagChunk  # noqa: E402
from app.services.chunking import build_page_chunk_records, normalize_arabic  # noqa: E402
from app.services.embeddings import embed_batch  # noqa: E402
from app.services.ingestion_pipeline import slugify_source  # noqa: E402
from app.services.reviewed_curriculum_metadata import (  # noqa: E402
    chunk_is_embedding_ready,
    ensure_reviewed_metadata_ready,
    metadata_with_reviewed_version,
)
from scripts.migration_guard import ensure_migrations_applied  # noqa: E402


def _default_pages_dir(source: ContentSource) -> Path:
    return PROJECT_DIR / "data" / "textbooks" / slugify_source(source.title) / "pages"


def _load_pages(pages_dir: Path) -> list[tuple[Path, dict]]:
    pages: list[tuple[Path, dict]] = []
    for path in sorted(pages_dir.glob("page_*.json")):
        pages.append((path, json.loads(path.read_text(encoding="utf-8"))))
    return pages


def _metadata_dict(source: ContentSource) -> dict:
    return dict(source.metadata_json) if isinstance(source.metadata_json, dict) else {}


async def rechunk_cached_source(
    *,
    source_id: int,
    pages_dir: Path | None,
    dry_run: bool,
    local_embeddings: bool,
) -> dict:
    ensure_migrations_applied(engine, required_tables=("alembic_version", "content_sources", "rag_chunks"))
    reviewed_metadata = ensure_reviewed_metadata_ready()
    db = SessionLocal()
    try:
        source = db.get(ContentSource, source_id)
        if source is None:
            raise SystemExit(f"ContentSource {source_id} was not found.")

        resolved_pages_dir = pages_dir or _default_pages_dir(source)
        if not resolved_pages_dir.exists():
            raise SystemExit(f"Pages directory was not found: {resolved_pages_dir}")

        pages = _load_pages(resolved_pages_dir)
        if not pages:
            raise SystemExit(f"No page_*.json files found in {resolved_pages_dir}")

        if local_embeddings:
            settings.gemini_api_key = ""
            settings.google_api_key = ""

        pending_records: list[tuple[int, dict, object]] = []
        empty_pages: list[int] = []
        incomplete_vision_pages: list[int] = []
        for _path, payload in pages:
            page_number = int(payload.get("page_number") or 0)
            records = build_page_chunk_records(payload)
            if not records:
                empty_pages.append(page_number)
                continue
            if payload.get("page_type") in {"NEEDS_VISION", "MIXED_VISION"} and payload.get("status") not in {
                "completed_with_vision",
                "completed_with_pdf_extraction",
                "completed_with_fallback_model",
                "completed_with_image_fallback",
            }:
                incomplete_vision_pages.append(page_number)
            for record in records:
                candidate = {
                    **(record.metadata or {}),
                    "source_type": source.source_type,
                }
                ready, reason, missing = chunk_is_embedding_ready(candidate, reviewed_metadata)
                if not ready:
                    raise RuntimeError(
                        "Refusing to embed cached chunks without reviewed curriculum metadata: "
                        + json.dumps(
                            {
                                "page_number": page_number,
                                "reason": reason,
                                "missing_metadata": missing,
                            },
                            ensure_ascii=False,
                        )
                    )
                pending_records.append((page_number, payload, record))

        if dry_run:
            return {
                "source_id": source.id,
                "source_title": source.title,
                "pages_dir": str(resolved_pages_dir),
                "pages_seen": len(pages),
                "pages_with_chunks": len({page for page, _payload, _record in pending_records}),
                "chunks_to_create": len(pending_records),
                "empty_pages": sorted(page for page in empty_pages if page),
                "incomplete_vision_pages_with_text": sorted(set(incomplete_vision_pages)),
                "local_embeddings": local_embeddings,
                "dry_run": True,
            }

        db.query(RagChunk).filter(RagChunk.source_id == source.id).delete(synchronize_session=False)
        embeddings = await embed_batch([record.content for _page, _payload, record in pending_records])

        for chunk_index, ((page_number, payload, record), embedding) in enumerate(zip(pending_records, embeddings)):
            db.add(
                RagChunk(
                    source_id=source.id,
                    chapter_id=None,
                    lesson_id=None,
                    topic_id=None,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    content=record.content,
                    normalized_content=normalize_arabic(record.content),
                    content_type=record.content_type,
                    source_type=source.source_type,
                    extraction_method=payload.get("extraction_method") or "+".join(payload.get("extraction_methods") or []),
                    language=payload.get("detected_language") or "ar",
                    embedding=embedding,
                    metadata_json=metadata_with_reviewed_version(record.metadata, reviewed_metadata),
                )
            )

        metadata = _metadata_dict(source)
        metadata["last_rechunk"] = {
            "at": datetime.now(timezone.utc).isoformat(),
            "pages_dir": str(resolved_pages_dir),
            "pages_seen": len(pages),
            "pages_with_chunks": len({page for page, _payload, _record in pending_records}),
            "chunks_created": len(pending_records),
            "empty_pages": sorted(page for page in empty_pages if page),
            "incomplete_vision_pages_with_text": sorted(set(incomplete_vision_pages)),
            "local_embeddings": local_embeddings,
            "chunking": "section_aware_v1",
        }
        source.metadata_json = metadata
        db.commit()

        return {
            "source_id": source.id,
            "source_title": source.title,
            "pages_dir": str(resolved_pages_dir),
            "pages_seen": len(pages),
            "pages_with_chunks": len({page for page, _payload, _record in pending_records}),
            "chunks_created": len(pending_records),
            "empty_pages": sorted(page for page in empty_pages if page),
            "incomplete_vision_pages_with_text": sorted(set(incomplete_vision_pages)),
            "local_embeddings": local_embeddings,
            "dry_run": False,
        }
    finally:
        db.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild RAG chunks from cached page JSON files.")
    parser.add_argument("--source-id", type=int, default=1)
    parser.add_argument("--pages-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--local-embeddings",
        action="store_true",
        help="Use deterministic local embeddings instead of calling Gemini embeddings.",
    )
    args = parser.parse_args()

    result = await rechunk_cached_source(
        source_id=args.source_id,
        pages_dir=args.pages_dir,
        dry_run=args.dry_run,
        local_embeddings=args.local_embeddings,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
