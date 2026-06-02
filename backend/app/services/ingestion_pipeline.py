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
from app.services.chunking import build_page_chunk_records, deduplicate_sections, normalize_arabic, section_text
from app.services.embeddings import embed_batch
from app.services.ocr import UploadedDocument, VisionExtractionProvider, get_vision_provider
from app.services.pdf_processor import (
    classify_pages,
    extract_selectable_text_page,
    render_page_to_image,
)

ProgressCallback = Callable[[int, str], None]
VISION_PAGE_TYPES = {"NEEDS_VISION", "MIXED_VISION"}
SUCCESS_PAGE_STATUSES = {
    "completed_text_only",
    "completed_with_vision",
    "completed_with_pdf_extraction",
    "completed_with_fallback_model",
    "completed_with_image_fallback",
}


def slugify_source(title: str) -> str:
    """Create a stable filesystem-safe source slug."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", title.strip()).strip("_").lower()
    return slug or "source"


def _final_ingestion_status(
    *,
    ingestion_mode: str,
    failed_pages: list[int],
    skipped_dry_run_pages: list[int],
) -> str:
    """Resolve source status without treating skipped vision dry runs as completed ingestion."""
    if ingestion_mode == "dry_run":
        return "dry_run_incomplete" if skipped_dry_run_pages or failed_pages else "dry_run_completed"

    if failed_pages:
        return "failed"

    return "completed"


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
        "raw_markdown": text,
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
    vision_source: str | None = None,
    uploaded_pdf: UploadedDocument | None = None,
    gemini_pdf_payload: dict | None = None,
    gemini_image_fallback_payload: dict | None = None,
) -> dict:
    """Build the normalized per-page extraction cache payload."""
    merged_content = _content_from_sections(sections)
    raw_markdown = (vision_payload or {}).get("raw_markdown") or merged_content or text_layer_content
    model_name = (vision_payload or {}).get("model_name")
    fallback_model_payload = (
        vision_payload
        if model_name and model_name == settings.gemini_document_fallback_model
        else None
    )
    return {
        "page_number": page_number,
        "page_type": page_type,
        "extraction_methods": extraction_methods,
        "extraction_method": "+".join(extraction_methods),
        "status": status,
        "text_layer_content": text_layer_content,
        "vision_content": vision_payload or {},
        "gemini_pdf_content": gemini_pdf_payload
        or (vision_payload if vision_source == "gemini_files_api_pdf" else {}),
        "gemini_fallback_model_content": fallback_model_payload or {},
        "gemini_image_fallback_content": gemini_image_fallback_payload
        or (vision_payload if vision_source == "gemini_rendered_image_300dpi" else {}),
        "merged_content": merged_content,
        "raw_markdown": raw_markdown,
        "sections": sections,
        "questions": questions,
        "diagrams": diagrams,
        "tables": tables,
        "equations": equations,
        "warnings": warnings,
        "errors": errors,
        "char_count": len(merged_content or raw_markdown),
        "completeness_score": completeness_score,
        "detected_language": (vision_payload or {}).get("detected_language") or "ar",
        "vision_provider": (vision_payload or {}).get("provider"),
        "vision_source": vision_source,
        "uploaded_pdf": uploaded_pdf.to_payload() if uploaded_pdf else None,
        "raw_text": (vision_payload or {}).get("raw_text"),
        "quality_report": (vision_payload or {}).get("quality_report") or {},
    }


def _has_structured_vision_content(payload: dict) -> bool:
    return bool(
        payload.get("sections")
        or payload.get("questions")
        or payload.get("diagrams")
        or payload.get("tables")
        or payload.get("equations")
    )


def _vision_payload_char_count(payload: dict) -> int:
    parts: list[str] = []
    parts.extend(str(section.get("content") or "") for section in payload.get("sections") or [])
    parts.extend(str(question.get("question_text") or "") for question in payload.get("questions") or [])
    parts.extend(str(diagram.get("description") or "") for diagram in payload.get("diagrams") or [])
    parts.extend(str(table.get("markdown") or "") for table in payload.get("tables") or [])
    parts.extend(str(equation.get("equation") or "") for equation in payload.get("equations") or [])
    return len("\n\n".join(part for part in parts if part))


def _vision_quality_issue(payload: dict) -> str | None:
    if not payload.get("schema_valid", True):
        return "invalid_schema"
    if not payload.get("sections"):
        return "empty_sections"
    if not _has_structured_vision_content(payload):
        return "empty_structured_content"

    char_count = payload.get("char_count")
    if char_count is None:
        char_count = _vision_payload_char_count(payload)
    if int(char_count or 0) < settings.gemini_min_page_chars:
        return f"very_low_char_count:{int(char_count or 0)}"

    completeness_score = payload.get("completeness_score")
    if completeness_score is not None and float(completeness_score) < settings.gemini_min_completeness_score:
        return f"low_completeness_score:{float(completeness_score):.2f}"
    return None


async def _extract_page(
    pdf_path: str,
    page_num: int,
    page_type: str,
    source_title: str,
    source_type: str,
    vision_provider: VisionExtractionProvider,
    ingestion_mode: str,
    vision_required: bool,
    uploaded_pdf: UploadedDocument | None = None,
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
            vision_source=None,
            uploaded_pdf=None,
        )
        return payload, "+".join(text_methods)

    extraction_methods = [] if page_type == "NEEDS_VISION" else [*text_methods]
    production_mode = ingestion_mode == "production"
    if not vision_provider.is_configured and page_type in VISION_PAGE_TYPES and vision_required:
        extraction_methods.append("gemini_document")
        warnings = ["Gemini document extraction is not configured. Vision page extraction was skipped."]
        errors = []
        status = "skipped_dry_run"
        completeness_score = 0.0 if page_type == "NEEDS_VISION" else 0.45
        if production_mode:
            status = "failed"
            errors.append(f"{page_type} page requires Gemini document extraction, but GEMINI_API_KEY is not configured.")
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
            vision_source=None,
            uploaded_pdf=None,
        )
        return payload, "+".join(extraction_methods)

    vision_result = None
    vision_source = None
    gemini_pdf_payload: dict | None = None
    gemini_image_fallback_payload: dict | None = None
    warnings: list[str] = []

    if uploaded_pdf:
        extraction_methods.append("gemini_pdf_file")
        try:
            vision_result = await vision_provider.extract_page_from_pdf(uploaded_pdf, page_num, source_type)
            vision_source = "gemini_files_api_pdf"
            gemini_pdf_payload = vision_result.to_payload()
            quality_issue = _vision_quality_issue(vision_result.to_payload())
            if quality_issue:
                warnings.append(
                    f"Gemini PDF extraction failed quality check ({quality_issue}); using 300 DPI image fallback."
                )
                vision_result = None
        except Exception as exc:
            warnings.append(f"Gemini PDF extraction failed; using 300 DPI image fallback: {exc}")
            vision_result = None

    if vision_result is None:
        image_path = render_page_to_image(pdf_path, page_num, _source_image_dir(source_title), dpi=300)
        vision_result = await vision_provider.extract_page(str(image_path), page_num, source_type)
        vision_source = "gemini_rendered_image_300dpi"
        gemini_image_fallback_payload = vision_result.to_payload()
        if "gemini_image_300dpi" not in extraction_methods:
            extraction_methods.append("gemini_image_300dpi")

    vision_payload = vision_result.to_payload()
    vision_sections = list(vision_payload.get("sections") or [])
    questions = list(vision_payload.get("questions") or [])
    diagrams = list(vision_payload.get("diagrams") or [])
    tables = list(vision_payload.get("tables") or [])
    equations = list(vision_payload.get("equations") or [])
    warnings.extend(vision_payload.get("warnings") or [])
    errors: list[str] = []

    if page_type == "MIXED_VISION" and text_sections:
        sections = deduplicate_sections(text_sections + vision_sections)
    else:
        sections = vision_sections

    has_vision_content = bool(vision_sections or diagrams or tables or equations or questions)
    quality_issue = _vision_quality_issue(vision_payload) if vision_required else None
    if vision_required and quality_issue:
        status = "failed" if production_mode else "skipped_dry_run"
        error = f"Gemini document extraction failed quality check: {quality_issue}."
        if production_mode:
            errors.append(error)
        else:
            warnings.append(error)
        completeness_score = 0.0 if page_type == "NEEDS_VISION" else 0.45
    elif has_vision_content:
        if vision_source == "gemini_rendered_image_300dpi":
            status = "completed_with_image_fallback"
        elif vision_payload.get("model_name") == settings.gemini_document_fallback_model:
            status = "completed_with_fallback_model"
        elif vision_source == "gemini_files_api_pdf":
            status = "completed_with_pdf_extraction"
        else:
            status = "completed_with_vision"
        completeness_score = 1.0
    elif text_sections:
        status = "completed_text_only"
        completeness_score = 0.75
        warnings.append("No Gemini document content was available; used text layer only.")
    else:
        status = "failed"
        completeness_score = 0.0
        errors.append("No text-layer or Gemini document content was extracted.")

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
        vision_source=vision_source,
        uploaded_pdf=uploaded_pdf,
        gemini_pdf_payload=gemini_pdf_payload,
        gemini_image_fallback_payload=gemini_image_fallback_payload,
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
    chunk_records = build_page_chunk_records(page_payload)

    embeddings = await embed_batch([record.content for record in chunk_records])
    for offset, (record, embedding) in enumerate(zip(chunk_records, embeddings)):
        db.add(
            RagChunk(
                source_id=source.id,
                chapter_id=chapter_id,
                lesson_id=lesson_id,
                topic_id=topic_id,
                page_number=page_num,
                chunk_index=chunk_index_start + offset,
                content=record.content,
                normalized_content=normalize_arabic(record.content),
                content_type=record.content_type,
                source_type=source.source_type,
                extraction_method=extraction_method,
                language=page_payload.get("detected_language") or "ar",
                embedding=embedding,
                metadata_json={
                    **record.metadata,
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
        uploaded_pdf: UploadedDocument | None = None

        if resolved_ingestion_mode == "production" and not vision_provider.is_configured:
            errors.append("GEMINI_API_KEY is required before production ingestion can run.")
            failed_pages.extend(range(1, pages_to_process + 1))
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
                "uploaded_pdf": None,
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
                "uploaded_pdf": None,
            }

        if vision_pages and vision_provider.is_configured:
            if progress_callback:
                progress_callback(4, "uploading source PDF to Gemini Files API")
            try:
                uploaded_pdf = await vision_provider.upload_pdf(pdf_path)
                if uploaded_pdf is None:
                    warnings.append("Gemini provider did not return an uploaded PDF handle; using image fallback.")
            except Exception as exc:
                warnings.append(f"Gemini Files API PDF upload failed; using image fallback for vision pages: {exc}")
                uploaded_pdf = None

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
                    uploaded_pdf,
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

        source.status = _final_ingestion_status(
            ingestion_mode=resolved_ingestion_mode,
            failed_pages=failed_pages,
            skipped_dry_run_pages=skipped_dry_run_pages,
        )
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
            "uploaded_pdf": uploaded_pdf.to_payload() if uploaded_pdf else None,
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
            "uploaded_pdf": uploaded_pdf.to_payload() if uploaded_pdf else None,
        }
    finally:
        if owns_db:
            session.close()
