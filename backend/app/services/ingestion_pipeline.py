"""End-to-end source ingestion pipeline for RAG."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import PROJECT_DIR, settings
from app.database import SessionLocal
from app.models.textbook import ContentSource, ExtractedQuestion, RagChunk
from app.services.chunking import deduplicate_sections, normalize_arabic, section_text, split_text
from app.services.embeddings import embed_batch
from app.services.ocr import VisionExtractionProvider, get_vision_provider
from app.services.pdf_processor import (
    classify_pages,
    extract_selectable_text_page,
    render_page_to_image,
)

ProgressCallback = Callable[[int, str], None]
VISION_PAGE_TYPES = {"NEEDS_VISION", "MIXED_VISION"}
SUCCESS_PAGE_STATUSES = {"completed_text_only", "completed_with_vision"}


def slugify_source(title: str) -> str:
    """Create a stable filesystem-safe source slug."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", title.strip()).strip("_").lower()
    return slug or "source"


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
    text = extract_selectable_text_page(pdf_path, page_num)
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


def _content_from_sections(sections: list[dict]) -> str:
    return "\n\n".join(section_text(section) for section in sections if section_text(section))


def _page_cache_payload(
    *,
    page_number: int,
    page_type: str,
    extraction_methods: list[str],
    status: str,
    text_layer_content: str,
    vision_payload: dict | None,
    sections: list[dict],
    questions: list[dict],
    diagrams: list[dict],
    tables: list[dict],
    equations: list[dict],
    warnings: list[str],
    errors: list[str],
    completeness_score: float,
) -> dict:
    """Build the normalized per-page extraction cache payload."""
    merged_content = _content_from_sections(sections)
    return {
        "page_number": page_number,
        "page_type": page_type,
        "extraction_methods": extraction_methods,
        "extraction_method": "+".join(extraction_methods),
        "status": status,
        "text_layer_content": text_layer_content,
        "vision_content": vision_payload or {},
        "merged_content": merged_content,
        "sections": sections,
        "questions": questions,
        "diagrams": diagrams,
        "tables": tables,
        "equations": equations,
        "warnings": warnings,
        "errors": errors,
        "char_count": len(merged_content),
        "completeness_score": completeness_score,
        "detected_language": (vision_payload or {}).get("detected_language") or "ar",
        "vision_provider": (vision_payload or {}).get("provider"),
        "raw_text": (vision_payload or {}).get("raw_text"),
    }


async def _extract_page(
    pdf_path: str,
    page_num: int,
    page_type: str,
    source_title: str,
    source_type: str,
    vision_provider: VisionExtractionProvider,
    ingestion_mode: str,
    vision_required: bool,
) -> tuple[dict, str]:
    """Extract one page and return structured payload plus extraction method."""
    text_payload = _structured_text_page(pdf_path, page_num)
    text_sections = text_payload.get("sections") or []
    text_layer_content = _content_from_sections(text_sections)
    text_methods = ["pymupdf", "pdfplumber"]

    if page_type == "SELECTABLE_TEXT":
        payload = _page_cache_payload(
            page_number=page_num,
            page_type=page_type,
            extraction_methods=text_methods,
            status="completed_text_only",
            text_layer_content=text_layer_content,
            vision_payload=None,
            sections=text_sections,
            questions=[],
            diagrams=[],
            tables=[],
            equations=[],
            warnings=[],
            errors=[],
            completeness_score=1.0,
        )
        return payload, "+".join(text_methods)

    extraction_methods = ["gemini_vision"] if page_type == "NEEDS_VISION" else [*text_methods, "gemini_vision"]
    production_mode = ingestion_mode == "production"
    if not vision_provider.is_configured and page_type in VISION_PAGE_TYPES and vision_required:
        warnings = ["Gemini Vision is not configured. Vision page extraction was skipped."]
        errors = []
        status = "skipped_dry_run"
        completeness_score = 0.0 if page_type == "NEEDS_VISION" else 0.45
        if production_mode:
            status = "failed"
            errors.append(f"{page_type} page requires Gemini Vision, but GEMINI_API_KEY is not configured.")
            warnings = []
        payload = _page_cache_payload(
            page_number=page_num,
            page_type=page_type,
            extraction_methods=extraction_methods,
            status=status,
            text_layer_content=text_layer_content,
            vision_payload=None,
            sections=text_sections if page_type == "MIXED_VISION" else [],
            questions=[],
            diagrams=[],
            tables=[],
            equations=[],
            warnings=warnings,
            errors=errors,
            completeness_score=completeness_score,
        )
        return payload, "+".join(extraction_methods)

    image_path = render_page_to_image(pdf_path, page_num, _source_image_dir(source_title))
    vision_result = await vision_provider.extract_page(str(image_path), page_num, source_type)
    vision_payload = vision_result.to_payload()
    vision_sections = list(vision_payload.get("sections") or [])
    questions = list(vision_payload.get("questions") or [])
    diagrams = list(vision_payload.get("diagrams") or [])
    tables = list(vision_payload.get("tables") or [])
    equations = list(vision_payload.get("equations") or [])
    warnings = list(vision_payload.get("warnings") or [])
    errors: list[str] = []

    if page_type == "MIXED_VISION" and text_sections:
        sections = deduplicate_sections(text_sections + vision_sections)
    else:
        sections = vision_sections

    has_vision_content = bool(vision_sections or diagrams or tables or equations or questions)
    if vision_required and not has_vision_content:
        status = "failed" if production_mode else "skipped_dry_run"
        error = "Gemini Vision returned no structured educational content."
        if production_mode:
            errors.append(error)
        else:
            warnings.append(error)
        completeness_score = 0.0 if page_type == "NEEDS_VISION" else 0.45
    elif has_vision_content:
        status = "completed_with_vision"
        completeness_score = 1.0
    elif text_sections:
        status = "completed_text_only"
        completeness_score = 0.75
        warnings.append("No Gemini Vision content was available; used text layer only.")
    else:
        status = "failed"
        completeness_score = 0.0
        errors.append("No text-layer or Gemini Vision content was extracted.")

    payload = _page_cache_payload(
        page_number=page_num,
        page_type=page_type,
        extraction_methods=extraction_methods,
        status=status,
        text_layer_content=text_layer_content,
        vision_payload=vision_payload,
        sections=sections,
        questions=questions,
        diagrams=diagrams,
        tables=tables,
        equations=equations,
        warnings=warnings,
        errors=errors,
        completeness_score=completeness_score,
    )
    return payload, "+".join(extraction_methods)


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
        content = section_text(section)
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
                    "extraction_methods": page_payload.get("extraction_methods") or [],
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
                metadata_json={"raw_answer_source": raw_answer_source},
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
    ingestion_mode: str | None = None,
    ocr_required_for_vision: bool | None = None,
    allow_partial_ingestion: bool | None = None,
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
    diagrams_extracted = 0
    tables_extracted = 0
    equations_extracted = 0
    pages_processed = 0
    pages_completed = 0
    failed_pages: list[int] = []
    skipped_dry_run_pages: list[int] = []
    page_statuses: list[dict] = []
    warnings: list[str] = []
    resolved_ingestion_mode = (ingestion_mode or settings.ingestion_mode or "production").strip().lower()
    if resolved_ingestion_mode not in {"production", "dry_run"}:
        raise ValueError("ingestion_mode must be 'production' or 'dry_run'")
    resolved_ocr_required = (
        settings.ocr_required_for_vision if ocr_required_for_vision is None else ocr_required_for_vision
    )
    resolved_allow_partial = (
        settings.allow_partial_ingestion if allow_partial_ingestion is None else allow_partial_ingestion
    )

    try:
        if progress_callback:
            progress_callback(1, "registering source")
        source = _get_or_create_source(session, pdf_path, title, source_type, grade, subject, year)
        vision_provider = get_vision_provider(ocr_provider_name)

        if progress_callback:
            progress_callback(3, "classifying pages")
        classification = classify_pages(pdf_path)
        total_pages = classification["total_pages"] or 1
        pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
        page_types = {item["page_number"]: item["page_type"] for item in classification["pages"]}
        selectable_text_pages = [page for page in range(1, pages_to_process + 1) if page_types.get(page) == "SELECTABLE_TEXT"]
        needs_vision_pages = [page for page in range(1, pages_to_process + 1) if page_types.get(page) == "NEEDS_VISION"]
        mixed_vision_pages = [page for page in range(1, pages_to_process + 1) if page_types.get(page) == "MIXED_VISION"]
        vision_pages = [*needs_vision_pages, *mixed_vision_pages]

        if (
            resolved_ingestion_mode == "production"
            and resolved_ocr_required
            and vision_pages
            and not vision_provider.is_configured
        ):
            errors.append("GEMINI_API_KEY is required before production ingestion can process vision pages.")
            failed_pages.extend(sorted(vision_pages))
            source.status = "failed"
            source.metadata_json = {
                "classification": classification,
                "max_pages": max_pages,
                "total_pages": total_pages,
                "pages_to_process": pages_to_process,
                "selectable_text_pages": len(selectable_text_pages),
                "needs_vision_pages": len(needs_vision_pages),
                "mixed_vision_pages": len(mixed_vision_pages),
                "pages_attempted": 0,
                "pages_completed": 0,
                "pages_failed": len(set(failed_pages)),
                "pages_skipped_dry_run": 0,
                "failed_pages": sorted(set(failed_pages)),
                "skipped_dry_run_pages": [],
                "page_statuses": [],
                "chunks_created": 0,
                "questions_extracted": 0,
                "diagrams_extracted": 0,
                "tables_extracted": 0,
                "equations_extracted": 0,
                "warnings": warnings,
                "errors": errors,
                "ingestion_mode": resolved_ingestion_mode,
                "ocr_required_for_vision": resolved_ocr_required,
                "allow_partial_ingestion": resolved_allow_partial,
                "vision_provider": vision_provider.name,
                "vision_provider_configured": vision_provider.is_configured,
            }
            session.commit()
            return {
                "source_id": source.id,
                "status": source.status,
                "chunks_created": 0,
                "questions_extracted": 0,
                "diagrams_extracted": 0,
                "tables_extracted": 0,
                "equations_extracted": 0,
                "pages_processed": 0,
                "pages_completed": 0,
                "pages_failed": len(set(failed_pages)),
                "pages_skipped_dry_run": 0,
                "failed_pages": sorted(set(failed_pages)),
                "skipped_dry_run_pages": [],
                "page_statuses": [],
                "warnings": warnings,
                "errors": errors,
                "classification": classification,
                "total_pages": total_pages,
                "pages_to_process": pages_to_process,
                "selectable_text_pages": len(selectable_text_pages),
                "needs_vision_pages": len(needs_vision_pages),
                "mixed_vision_pages": len(mixed_vision_pages),
                "ingestion_mode": resolved_ingestion_mode,
                "ocr_required_for_vision": resolved_ocr_required,
                "allow_partial_ingestion": resolved_allow_partial,
                "ocr_provider": vision_provider.name,
                "ocr_provider_configured": vision_provider.is_configured,
                "vision_provider": vision_provider.name,
                "vision_provider_configured": vision_provider.is_configured,
            }

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
                    source.source_type,
                    vision_provider,
                    resolved_ingestion_mode,
                    resolved_ocr_required,
                )
                page_payload["classification"] = page_type
                page_payload["source_id"] = source.id
                _write_page_cache(source.title, page_num, page_payload)

                page_status = page_payload.get("status") or "failed"
                page_statuses.append(
                    {
                        "page_number": page_num,
                        "page_type": page_type,
                        "status": page_status,
                        "extraction_method": page_payload.get("extraction_method") or method,
                        "char_count": page_payload.get("char_count") or 0,
                        "completeness_score": page_payload.get("completeness_score") or 0.0,
                    }
                )
                page_failed = page_status not in SUCCESS_PAGE_STATUSES
                if page_failed:
                    failed_pages.append(page_num)
                    if page_status == "skipped_dry_run":
                        skipped_dry_run_pages.append(page_num)
                    for error in page_payload.get("errors") or [f"page status: {page_status}"]:
                        errors.append(f"page {page_num}: {error}")
                else:
                    pages_completed += 1
                warnings.extend(f"page {page_num}: {warning}" for warning in page_payload.get("warnings") or [])
                diagrams_extracted += len(page_payload.get("diagrams") or [])
                tables_extracted += len(page_payload.get("tables") or [])
                equations_extracted += len(page_payload.get("equations") or [])

                can_store_page = not page_failed or resolved_allow_partial or resolved_ingestion_mode == "dry_run"
                if can_store_page and page_payload.get("char_count", 0) > 0:
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
            except Exception as exc:
                session.rollback()
                errors.append(f"page {page_num}: {exc}")
                failed_pages.append(page_num)
                page_statuses.append(
                    {
                        "page_number": page_num,
                        "page_type": page_types.get(page_num, "NEEDS_VISION"),
                        "status": "failed",
                        "extraction_method": "exception",
                        "char_count": 0,
                        "completeness_score": 0.0,
                    }
                )
                failed_payload = _page_cache_payload(
                    page_number=page_num,
                    page_type=page_types.get(page_num, "NEEDS_VISION"),
                    extraction_methods=["exception"],
                    status="failed",
                    text_layer_content="",
                    vision_payload=None,
                    sections=[],
                    questions=[],
                    diagrams=[],
                    tables=[],
                    equations=[],
                    warnings=[],
                    errors=[str(exc)],
                    completeness_score=0.0,
                )
                failed_payload["classification"] = page_types.get(page_num, "NEEDS_VISION")
                failed_payload["source_id"] = source.id
                _write_page_cache(source.title, page_num, failed_payload)
            pages_processed += 1
            if progress_callback:
                progress = 5 + int((pages_processed / pages_to_process) * 95)
                progress_callback(min(progress, 100), f"processed page {page_num}/{pages_to_process}")

        if not failed_pages:
            source.status = "completed"
        elif resolved_allow_partial or resolved_ingestion_mode == "dry_run":
            source.status = "completed_with_warnings"
        else:
            source.status = "failed"
        source.metadata_json = {
            "classification": classification,
            "max_pages": max_pages,
            "total_pages": total_pages,
            "pages_to_process": pages_to_process,
            "selectable_text_pages": len(selectable_text_pages),
            "needs_vision_pages": len(needs_vision_pages),
            "mixed_vision_pages": len(mixed_vision_pages),
            "pages_attempted": pages_processed,
            "pages_completed": pages_completed,
            "pages_failed": len(set(failed_pages)),
            "pages_skipped_dry_run": len(set(skipped_dry_run_pages)),
            "failed_pages": sorted(set(failed_pages)),
            "skipped_dry_run_pages": sorted(set(skipped_dry_run_pages)),
            "page_statuses": page_statuses,
            "chunks_created": chunks_created,
            "questions_extracted": questions_extracted,
            "diagrams_extracted": diagrams_extracted,
            "tables_extracted": tables_extracted,
            "equations_extracted": equations_extracted,
            "warnings": warnings,
            "errors": errors,
            "ingestion_mode": resolved_ingestion_mode,
            "ocr_required_for_vision": resolved_ocr_required,
            "allow_partial_ingestion": resolved_allow_partial,
            "vision_provider": vision_provider.name,
            "vision_provider_configured": vision_provider.is_configured,
        }
        session.commit()
        return {
            "source_id": source.id,
            "status": source.status,
            "chunks_created": chunks_created,
            "questions_extracted": questions_extracted,
            "diagrams_extracted": diagrams_extracted,
            "tables_extracted": tables_extracted,
            "equations_extracted": equations_extracted,
            "pages_processed": pages_processed,
            "pages_completed": pages_completed,
            "pages_failed": len(set(failed_pages)),
            "pages_skipped_dry_run": len(set(skipped_dry_run_pages)),
            "failed_pages": sorted(set(failed_pages)),
            "skipped_dry_run_pages": sorted(set(skipped_dry_run_pages)),
            "page_statuses": page_statuses,
            "warnings": warnings,
            "errors": errors,
            "classification": classification,
            "total_pages": total_pages,
            "pages_to_process": pages_to_process,
            "selectable_text_pages": len(selectable_text_pages),
            "needs_vision_pages": len(needs_vision_pages),
            "mixed_vision_pages": len(mixed_vision_pages),
            "ingestion_mode": resolved_ingestion_mode,
            "ocr_required_for_vision": resolved_ocr_required,
            "allow_partial_ingestion": resolved_allow_partial,
            "ocr_provider": vision_provider.name,
            "ocr_provider_configured": vision_provider.is_configured,
            "vision_provider": vision_provider.name,
            "vision_provider_configured": vision_provider.is_configured,
        }
    finally:
        if owns_db:
            session.close()
