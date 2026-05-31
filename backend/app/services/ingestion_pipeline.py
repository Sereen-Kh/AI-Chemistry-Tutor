"""End-to-end source ingestion pipeline for RAG."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import PROJECT_DIR
from app.database import SessionLocal
from app.models.textbook import ContentSource, ExtractedQuestion, RagChunk
from app.services.embeddings import embed_batch
from app.services.ocr import OCRProvider, get_ocr_provider
from app.services.pdf_processor import (
    classify_pages,
    extract_text_page,
    render_page_image_file,
)

ProgressCallback = Callable[[int, str], None]


def slugify_source(title: str) -> str:
    """Create a stable filesystem-safe source slug."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", title.strip()).strip("_").lower()
    return slug or "source"


def split_text(text: str, chunk_size: int = 650, chunk_overlap: int = 90) -> list[str]:
    """Split Arabic educational text into overlapping retrieval chunks."""
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        hard_end = min(start + chunk_size, length)
        end = hard_end
        if hard_end < length:
            candidates = [normalized.rfind(sep, start, hard_end) for sep in ["\n\n", "\n", ".", "؟", "،", " "]]
            best = max(candidates)
            if best > start + chunk_size // 2:
                end = best + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(0, end - chunk_overlap)
    return chunks


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text lightly for retrieval while preserving source text separately."""
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "\u0640": "",
    }
    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return re.sub(r"\s+", " ", normalized).strip()


def _source_cache_dir(title: str) -> Path:
    return PROJECT_DIR / "data" / "textbooks" / slugify_source(title) / "pages"


def _source_image_dir(title: str) -> Path:
    return PROJECT_DIR / "data" / "textbooks" / slugify_source(title) / "page_images"


def _write_page_cache(title: str, page_num: int, payload: dict) -> None:
    cache_dir = _source_cache_dir(title)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"page_{page_num:03d}.json"
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _structured_text_page(pdf_path: str, page_num: int) -> dict:
    text = extract_text_page(pdf_path, page_num)
    return {
        "page_number": page_num,
        "detected_language": "ar",
        "sections": [
            {
                "heading": None,
                "content": text,
                "content_type": "text",
            }
        ]
        if text
        else [],
        "questions": [],
        "diagrams": [],
        "tables": [],
        "equations": [],
        "warnings": [],
    }


async def _extract_page(
    pdf_path: str,
    page_num: int,
    page_type: str,
    source_title: str,
    ocr_provider: OCRProvider,
) -> tuple[dict, str]:
    """Extract one page and return structured payload plus extraction method."""
    if page_type == "SELECTABLE_TEXT":
        return _structured_text_page(pdf_path, page_num), "pdf_text"

    image_path = render_page_image_file(pdf_path, page_num, _source_image_dir(source_title))
    ocr_result = await ocr_provider.extract_page(str(image_path), page_num)
    structured = ocr_result.to_payload()
    method = ocr_provider.name if ocr_provider.is_configured else "ocr_unavailable"

    if not structured.get("sections"):
        fallback_payload = _structured_text_page(pdf_path, page_num)
        if fallback_payload["sections"]:
            structured["sections"] = fallback_payload["sections"]
            structured["warnings"] = (structured.get("warnings") or []) + [
                "OCR produced no sections; used text-layer fallback."
            ]
            method = "pdf_text_fallback"

    if page_type == "MIXED_VISION":
        text_payload = _structured_text_page(pdf_path, page_num)
        if text_payload["sections"]:
            structured["sections"] = text_payload["sections"] + structured.get("sections", [])
    return structured, method


def _section_text(section: dict) -> str:
    heading = section.get("heading")
    content = section.get("content") or ""
    return f"{heading}\n{content}".strip() if heading else content.strip()


async def _store_page_chunks(
    db: Session,
    source: ContentSource,
    page_num: int,
    page_payload: dict,
    chapter_id: int | None,
    lesson_id: int | None,
    topic_id: int | None,
    extraction_method: str,
    chunk_index_start: int,
) -> int:
    """Create RagChunk rows for one extracted page and return chunks created."""
    chunk_records: list[tuple[str, str, dict]] = []
    for section in page_payload.get("sections") or []:
        content = _section_text(section)
        content_type = section.get("content_type") or "text"
        for chunk in split_text(content):
            chunk_records.append((chunk, content_type, {"section_heading": section.get("heading")}))

    for table in page_payload.get("tables") or []:
        markdown = table.get("markdown") or ""
        for chunk in split_text(markdown):
            chunk_records.append((chunk, "table", {"table_title": table.get("title")}))

    for diagram in page_payload.get("diagrams") or []:
        description = diagram.get("description") or ""
        labels = ", ".join(str(label) for label in diagram.get("labels") or [])
        related = diagram.get("related_text") or ""
        content = "\n".join(part for part in [diagram.get("title"), description, labels, related] if part)
        for chunk in split_text(content):
            chunk_records.append((chunk, "diagram", {"diagram_title": diagram.get("title")}))

    for equation in page_payload.get("equations") or []:
        content = "\n".join(part for part in [equation.get("equation"), equation.get("description")] if part)
        for chunk in split_text(content):
            chunk_records.append((chunk, "equation", {}))

    embeddings = await embed_batch([record[0] for record in chunk_records])
    for offset, ((content, content_type, metadata), embedding) in enumerate(zip(chunk_records, embeddings)):
        db.add(
            RagChunk(
                source_id=source.id,
                chapter_id=chapter_id,
                lesson_id=lesson_id,
                topic_id=topic_id,
                page_number=page_num,
                chunk_index=chunk_index_start + offset,
                content=content,
                normalized_content=normalize_arabic(content),
                content_type=content_type,
                source_type=source.source_type,
                extraction_method=extraction_method,
                language=page_payload.get("detected_language") or "ar",
                embedding=embedding,
                metadata_json={
                    **metadata,
                    "warnings": page_payload.get("warnings") or [],
                },
            )
        )
    return len(chunk_records)


def _store_questions(
    db: Session,
    source: ContentSource,
    page_num: int,
    page_payload: dict,
    chapter_id: int | None,
    lesson_id: int | None,
    topic_id: int | None,
) -> int:
    """Persist questions extracted from a page."""
    created = 0
    for question in page_payload.get("questions") or []:
        question_text = (question.get("question_text") or "").strip()
        if not question_text:
            continue
        correct_answer = question.get("correct_answer")
        answer_source = "book" if correct_answer and question.get("answer_source") == "page" else "unknown"
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
                needs_review=answer_source != "book",
                metadata_json={"raw_answer_source": question.get("answer_source")},
            )
        )
        created += 1
    return created


def _get_or_create_source(
    db: Session,
    pdf_path: str,
    title: str | None,
    source_type: str,
    grade: str,
    subject: str,
    year: int | None,
) -> ContentSource:
    path = str(Path(pdf_path).expanduser())
    source = db.query(ContentSource).filter(ContentSource.file_path == path, ContentSource.source_type == source_type).first()
    if source:
        source.status = "processing"
        source.title = title or source.title
        source.grade = grade
        source.subject = subject
        source.year = year
    else:
        source = ContentSource(
            source_type=source_type,
            title=title or Path(pdf_path).stem,
            grade=grade,
            subject=subject,
            year=year,
            file_path=path,
            original_filename=Path(pdf_path).name,
            status="processing",
            metadata_json={},
        )
        db.add(source)
    db.commit()
    db.refresh(source)
    return source


async def run_full_ingestion(
    pdf_path: str,
    chapter_id: int | None = None,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    source_type: str = "textbook",
    title: str | None = None,
    grade: str = "grade_9",
    subject: str = "chemistry",
    year: int | None = None,
    max_pages: int | None = None,
    ocr_provider_name: str | None = None,
    clear_existing: bool = False,
    progress_callback: ProgressCallback | None = None,
    db: Session | None = None,
) -> dict:
    """Classify, extract, cache, chunk, embed, and store a source PDF."""
    owns_db = db is None
    session = db or SessionLocal()
    errors: list[str] = []
    chunks_created = 0
    questions_extracted = 0
    pages_processed = 0

    try:
        if progress_callback:
            progress_callback(1, "registering source")
        source = _get_or_create_source(session, pdf_path, title, source_type, grade, subject, year)
        ocr_provider = get_ocr_provider(ocr_provider_name)

        if progress_callback:
            progress_callback(3, "classifying pages")
        classification = classify_pages(pdf_path)
        total_pages = classification["total_pages"] or 1
        pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
        page_types = {item["page_number"]: item["page_type"] for item in classification["pages"]}

        if clear_existing:
            session.query(RagChunk).filter(RagChunk.source_id == source.id).delete(synchronize_session=False)
            session.query(ExtractedQuestion).filter(ExtractedQuestion.source_id == source.id).delete(
                synchronize_session=False
            )
            session.commit()

        for page_num in range(1, pages_to_process + 1):
            try:
                page_type = page_types.get(page_num, "NEEDS_VISION")
                page_payload, method = await _extract_page(
                    pdf_path,
                    page_num,
                    page_type,
                    source.title,
                    ocr_provider,
                )
                page_payload["classification"] = page_type
                page_payload["source_id"] = source.id
                _write_page_cache(source.title, page_num, page_payload)

                created = await _store_page_chunks(
                    session,
                    source,
                    page_num,
                    page_payload,
                    chapter_id,
                    lesson_id,
                    topic_id,
                    method,
                    chunks_created,
                )
                chunks_created += created
                questions_extracted += _store_questions(
                    session,
                    source,
                    page_num,
                    page_payload,
                    chapter_id,
                    lesson_id,
                    topic_id,
                )
                session.commit()
                pages_processed += 1
            except Exception as exc:
                session.rollback()
                errors.append(f"page {page_num}: {exc}")
            if progress_callback:
                progress = 5 + int((pages_processed / pages_to_process) * 95)
                progress_callback(min(progress, 100), f"processed page {page_num}/{pages_to_process}")

        source.status = "completed" if not errors else "failed"
        source.metadata_json = {
            "classification": classification,
            "max_pages": max_pages,
            "pages_completed": pages_processed,
            "pages_failed": len(errors),
            "chunks_created": chunks_created,
            "questions_extracted": questions_extracted,
            "errors": errors,
            "ocr_provider": ocr_provider.name,
            "ocr_provider_configured": ocr_provider.is_configured,
        }
        session.commit()
        return {
            "source_id": source.id,
            "chunks_created": chunks_created,
            "questions_extracted": questions_extracted,
            "pages_processed": pages_processed,
            "pages_failed": len(errors),
            "errors": errors,
            "classification": classification,
            "ocr_provider": ocr_provider.name,
            "ocr_provider_configured": ocr_provider.is_configured,
        }
    finally:
        if owns_db:
            session.close()
