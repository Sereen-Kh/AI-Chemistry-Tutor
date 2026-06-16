"""Rebuild retrievable RAG chunks from cached per-page extraction JSON."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import PROJECT_DIR
from app.models.ingestion import IngestionPage
from app.models.textbook import ContentSource, ExtractedQuestion, RagChunk
from app.services.chunking import build_page_chunk_records, normalize_arabic
from app.services.embeddings import current_embedding_model_name, embed_batch, embedding_provider_status


@dataclass
class CachedPageRebuildResult:
    """Summary returned by cached-page RAG rebuilds."""

    source_id: int
    source_title: str
    source_status: str
    cache_dir: str
    total_cache_pages: int
    readable_pages: int
    stored_pages: int
    empty_pages: int
    failed_pages: list[int] = field(default_factory=list)
    skipped_pages: list[int] = field(default_factory=list)
    chunks_deleted: int = 0
    questions_deleted: int = 0
    chunks_created: int = 0
    questions_created: int = 0
    content_type_counts: dict[str, int] = field(default_factory=dict)
    embedding_provider: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def default_chemistry_cache_dir() -> Path:
    return PROJECT_DIR / "data" / "textbooks" / "syria_grade_9_chemistry" / "pages"


def default_chemistry_pdf_path() -> Path:
    return PROJECT_DIR / "data" / "textbooks" / "syria_grade_9" / "Chemistry.pdf"


def _resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    project_candidate = PROJECT_DIR / candidate
    if project_candidate.exists():
        return project_candidate
    backend_candidate = PROJECT_DIR / "backend" / candidate
    if backend_candidate.exists():
        return backend_candidate
    return project_candidate


def _page_number_from_path(path: Path, payload: dict) -> int:
    if payload.get("page_number"):
        return int(payload["page_number"])
    return int(path.stem.split("_")[-1])


def _page_char_count(payload: dict) -> int:
    explicit = int(payload.get("char_count") or 0)
    if explicit > 0:
        return explicit
    fallback = (
        payload.get("merged_content")
        or payload.get("raw_markdown")
        or payload.get("text_layer_content")
        or payload.get("raw_text")
        or ""
    )
    return len(str(fallback).strip())


def _page_preview(payload: dict) -> str:
    text = (
        payload.get("merged_content")
        or payload.get("raw_markdown")
        or payload.get("text_layer_content")
        or payload.get("raw_text")
        or ""
    )
    return " ".join(str(text).split())[:400]


def _get_or_create_cached_source(
    db: Session,
    *,
    title: str,
    source_type: str,
    grade: str,
    subject: str,
    year: int | None,
    file_path: str | None,
) -> ContentSource:
    source = (
        db.query(ContentSource)
        .filter(ContentSource.title == title, ContentSource.source_type == source_type)
        .first()
    )
    if source is None and file_path:
        source = (
            db.query(ContentSource)
            .filter(ContentSource.file_path == file_path, ContentSource.source_type == source_type)
            .first()
        )
    if source is None:
        source = ContentSource(
            title=title,
            source_type=source_type,
            grade=grade,
            subject=subject,
            year=year,
            file_path=file_path,
            original_filename=Path(file_path).name if file_path else None,
            status="processing",
            metadata_json={},
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    else:
        source.title = title
        source.source_type = source_type
        source.grade = grade
        source.subject = subject
        source.year = year
        source.file_path = file_path or source.file_path
        source.status = "processing"
        db.commit()
        db.refresh(source)
    return source


def _store_cached_questions(
    db: Session,
    source: ContentSource,
    page_num: int,
    page_payload: dict,
    chapter_id: int | None,
    lesson_id: int | None,
    topic_id: int | None,
) -> int:
    created = 0
    for question in page_payload.get("questions") or []:
        question_text = str(question.get("question_text") or "").strip()
        if not question_text:
            continue
        correct_answer = question.get("correct_answer")
        raw_answer_source = question.get("answer_source")
        answer_source = raw_answer_source if correct_answer and raw_answer_source in {"page", "answer_key"} else "unknown"
        db.add(
            ExtractedQuestion(
                source_id=source.id,
                chapter_id=chapter_id,
                lesson_id=lesson_id,
                topic_id=topic_id,
                page_number=page_num,
                question_text=question_text,
                question_type=question.get("question_type") or "unknown",
                options=question.get("options"),
                correct_answer=correct_answer,
                explanation=question.get("explanation"),
                answer_source=answer_source,
                difficulty=question.get("difficulty"),
                needs_review=answer_source not in {"page", "answer_key"},
                metadata_json={"raw_answer_source": raw_answer_source, "cache_rebuild": True},
            )
        )
        created += 1
    return created


async def rebuild_rag_chunks_from_cached_pages(
    db: Session,
    *,
    cache_dir: str | Path | None = None,
    title: str = "syria_grade_9_chemistry",
    source_type: str = "textbook",
    grade: str = "grade_9",
    subject: str = "chemistry",
    year: int | None = None,
    file_path: str | Path | None = None,
    chapter_id: int | None = None,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    clear_existing: bool = True,
    refresh_ingestion_pages: bool = True,
) -> CachedPageRebuildResult:
    """Clear and rebuild RAG chunks from cached ``page_NNN.json`` files."""

    resolved_cache_dir = _resolve_project_path(cache_dir) if cache_dir else default_chemistry_cache_dir()
    resolved_cache_dir = resolved_cache_dir.resolve()
    if not resolved_cache_dir.exists():
        raise FileNotFoundError(f"Cached page directory not found: {resolved_cache_dir}")

    resolved_file_path = str(_resolve_project_path(file_path)) if file_path else str(default_chemistry_pdf_path())
    source = _get_or_create_cached_source(
        db,
        title=title,
        source_type=source_type,
        grade=grade,
        subject=subject,
        year=year,
        file_path=resolved_file_path,
    )

    chunks_deleted = 0
    questions_deleted = 0
    if clear_existing:
        chunks_deleted = db.query(RagChunk).filter(RagChunk.source_id == source.id).delete(synchronize_session=False)
        questions_deleted = (
            db.query(ExtractedQuestion).filter(ExtractedQuestion.source_id == source.id).delete(synchronize_session=False)
        )
        if refresh_ingestion_pages:
            db.query(IngestionPage).filter(IngestionPage.source_id == source.id).delete(synchronize_session=False)
        db.commit()

    chunk_index = 0
    chunks_created = 0
    questions_created = 0
    stored_pages: set[int] = set()
    readable_pages: set[int] = set()
    failed_pages: list[int] = []
    skipped_pages: list[int] = []
    content_type_counter: Counter[str] = Counter()
    page_statuses: list[dict] = []

    page_files = sorted(resolved_cache_dir.glob("page_*.json"))
    for page_file in page_files:
        try:
            payload = json.loads(page_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            skipped_pages.append(int(page_file.stem.split("_")[-1]))
            continue

        page_num = _page_number_from_path(page_file, payload)
        char_count = _page_char_count(payload)
        status = str(payload.get("status") or "unknown")
        page_type = str(payload.get("page_type") or payload.get("classification") or "unknown")
        if status == "failed" or char_count <= 0:
            failed_pages.append(page_num)
            if refresh_ingestion_pages:
                db.add(
                    IngestionPage(
                        source_id=source.id,
                        page_number=page_num,
                        page_type=page_type,
                        status=status,
                        extraction_methods=payload.get("extraction_methods") or [],
                        cache_path=str(page_file),
                        char_count=max(char_count, 0),
                        completeness_score=float(payload.get("completeness_score") or 0.0),
                        warnings_json=payload.get("warnings") or [],
                        errors_json=payload.get("errors") or [],
                        content_preview=None,
                    )
                )
            continue

        readable_pages.add(page_num)
        chunk_records = build_page_chunk_records(payload)
        if not chunk_records:
            skipped_pages.append(page_num)
            continue

        embeddings = await embed_batch([record.content for record in chunk_records])
        for offset, (record, embedding) in enumerate(zip(chunk_records, embeddings)):
            content_type_counter[record.content_type] += 1
            db.add(
                RagChunk(
                    source_id=source.id,
                    chapter_id=chapter_id,
                    lesson_id=lesson_id,
                    topic_id=topic_id,
                    page_number=page_num,
                    chunk_index=chunk_index + offset,
                    content=record.content,
                    normalized_content=normalize_arabic(record.content),
                    content_type=record.content_type,
                    source_type=source.source_type,
                    extraction_method=str(payload.get("extraction_method") or "+".join(payload.get("extraction_methods") or [])),
                    language=str(payload.get("detected_language") or "ar")[:8],
                    embedding=embedding,
                    embedding_model=current_embedding_model_name(),
                    embedding_updated_at=datetime.now(timezone.utc),
                    metadata_json={
                        **record.metadata,
                        "cache_path": str(page_file),
                        "cache_rebuild": True,
                        "embedding_model": current_embedding_model_name(),
                        "extraction_methods": payload.get("extraction_methods") or [],
                        "warnings": payload.get("warnings") or [],
                    },
                )
            )
        chunk_index += len(chunk_records)
        chunks_created += len(chunk_records)
        questions_created += _store_cached_questions(db, source, page_num, payload, chapter_id, lesson_id, topic_id)
        stored_pages.add(page_num)

        if refresh_ingestion_pages:
            db.add(
                IngestionPage(
                    source_id=source.id,
                    page_number=page_num,
                    page_type=page_type,
                    status=status,
                    extraction_methods=payload.get("extraction_methods") or [],
                    cache_path=str(page_file),
                    char_count=char_count,
                    completeness_score=float(payload.get("completeness_score") or 0.0),
                    warnings_json=payload.get("warnings") or [],
                    errors_json=payload.get("errors") or [],
                    content_preview=_page_preview(payload),
                )
            )
        page_statuses.append(
            {
                "page_number": page_num,
                "page_type": page_type,
                "status": status,
                "char_count": char_count,
                "chunks_created": len(chunk_records),
            }
        )

    empty_pages = max(len(page_files) - len(readable_pages), 0)
    source.status = "completed_with_warnings" if failed_pages or skipped_pages else "completed"
    source.metadata_json = {
        **(source.metadata_json or {}),
        "rebuild_from_cache": True,
        "cache_dir": str(resolved_cache_dir),
        "total_cache_pages": len(page_files),
        "readable_pages": len(readable_pages),
        "stored_pages": len(stored_pages),
        "empty_pages": empty_pages,
        "failed_pages": sorted(set(failed_pages)),
        "skipped_pages": sorted(set(skipped_pages)),
        "chunks_created": chunks_created,
        "questions_created": questions_created,
        "content_type_counts": dict(content_type_counter),
        "embedding_provider": embedding_provider_status(),
        "page_statuses": page_statuses,
    }
    db.commit()
    db.refresh(source)

    return CachedPageRebuildResult(
        source_id=source.id,
        source_title=source.title,
        source_status=source.status,
        cache_dir=str(resolved_cache_dir),
        total_cache_pages=len(page_files),
        readable_pages=len(readable_pages),
        stored_pages=len(stored_pages),
        empty_pages=empty_pages,
        failed_pages=sorted(set(failed_pages)),
        skipped_pages=sorted(set(skipped_pages)),
        chunks_deleted=chunks_deleted,
        questions_deleted=questions_deleted,
        chunks_created=chunks_created,
        questions_created=questions_created,
        content_type_counts=dict(content_type_counter),
        embedding_provider=embedding_provider_status(),
    )
