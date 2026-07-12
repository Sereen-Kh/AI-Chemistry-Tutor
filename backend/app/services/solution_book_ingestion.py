"""Chemistry solution book ingestion pipeline.

This module keeps solution-book ingestion separate from the existing textbook
pipeline while using the same production storage primitives: ``ContentSource``,
``RagChunk``, configured embeddings, and PostgreSQL/pgvector when available.
It also writes deterministic processed JSONL artifacts for inspection.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
from statistics import mean
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import PROJECT_DIR, settings
from app.database import SessionLocal
from app.models.textbook import ContentSource, RagChunk
from app.services.chunking import ChunkRecord, extract_formula_terms, split_solution_book_text
from app.services.embeddings import EMBEDDING_DIM, current_embedding_model_name, embed_batch, embedding_provider_status
from app.services.ocr import get_vision_provider
from app.services.ocr.normalization import normalize_text
from app.services.pdf_processor import detect_visual_content, extract_text_page, render_page_to_image
from app.services.reviewed_curriculum_metadata import (
    chunk_is_embedding_ready,
    ensure_reviewed_metadata_ready,
    metadata_with_reviewed_version,
)

logger = logging.getLogger(__name__)

SOURCE_TYPE = "solution_book"
DEFAULT_DOCUMENT_ID = "chemistry_grade9_solution_book"
DEFAULT_TITLE = "Chemistry Solution Book - Grade 9"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "data" / "processed" / "solution_book"
DEFAULT_PDF_PATH = PROJECT_DIR / "data" / "textbooks" / "solution-book" / "Chemistry_Solution_Book.pdf"
_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_EQUATION_HINT_RE = re.compile(
    r"(?:[A-Z][a-z]?[0-9₀-₉]*\s*(?:[+=→⟶⇌]|->)|"
    r"(?:Cm|C|n|m|V|M)\s*=|mol/L|g/L|mL|HCl|NaOH|H₂SO₄|H2SO4|CO₂|CO2)"
)
_UNIT_START_RE = re.compile(
    r"(?=^\s*(?:السؤال|سؤال|تمرين|المسألة|مسالة|المطلوب)\s*"
    r"(?:(?:رقم|الأول|الاول|الثاني|الثالث|الرابع|الخامس)\s*)?"
    r"(?:[\d٠-٩]+|[اأإآبجدهوزحطيكلمنسعفصقرشتثخذضظغ])?[:：.)\-]?)",
    re.MULTILINE,
)
_LESSON_RE = re.compile(r"(?:الدرس|درس)\s+([^\n:：]{2,80})")
_CHAPTER_RE = re.compile(r"(?:الفصل|الوحدة|الباب)\s+([^\n:：]{2,80})")
_QUESTION_NO_RE = re.compile(
    r"(?:السؤال|سؤال|تمرين|المسألة|مسالة)\s*"
    r"(?:(?:رقم)\s*)?([\d٠-٩]+|[اأإآبجدهوزحطيكلمنسعفصقرشتثخذضظغ]+)?"
)
_PAGE_REF_RE = re.compile(r"(?:صفحة|ص\.?)\s*([\d٠-٩]+)")
_EQUATION_LINE_RE = re.compile(r".*(?:=|→|⟶|⇌|->).*(?:[A-Z][a-z]?[0-9₀-₉]*|\d).*")
_FINAL_ANSWER_RE = re.compile(r"(?:الجواب النهائي|الإجابة النهائية|النتيجة|إذن|وعليه)[:：]?\s*(.+)")


@dataclass(frozen=True)
class PageExtractionQuality:
    page_number: int
    text_length: int
    arabic_ratio: float
    weird_char_ratio: float
    line_count: int
    has_equation_like_text: bool
    has_images: bool
    has_tables: bool
    needs_ocr: bool
    needs_vision: bool
    confidence: float
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExtractedSolutionPage:
    document_id: str
    source_type: str
    page_number: int
    text: str
    normalized_text: str
    extraction_method: str
    quality: PageExtractionQuality
    images: list[dict[str, Any]]
    metadata: dict[str, Any]
    status: str
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SolutionUnit:
    id: str
    document_id: str
    source_type: str
    chapter_title: str | None
    lesson_title: str | None
    page_number: int
    exercise_number: str | None
    question_number: str | None
    question_text: str | None
    solution_text: str
    solution_steps: list[str]
    final_answer: str | None
    equations: list[str]
    keywords: list[str]
    related_textbook_pages: list[int]
    extraction_confidence: float


@dataclass(frozen=True)
class SolutionBookChunk:
    id: str
    document_id: str
    source_type: str
    chunk_type: str
    chapter_title: str | None
    lesson_title: str | None
    page_start: int
    page_end: int
    exercise_number: str | None
    question_number: str | None
    content: str
    content_ar: str
    keywords: list[str]
    equations: list[str]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SolutionBookIngestionResult:
    status: str
    mode: str
    document_id: str
    source_type: str
    source_id: int | None
    pdf_path: str
    output_dir: str
    source_file_hash: str
    pages_total: int
    pages_extracted_digitally: int
    pages_needing_ocr: int
    pages_needing_vision: int
    blocked_pages: list[int]
    solution_units: int
    chunks: int
    chunks_inserted: int
    chunks_skipped_duplicate: int
    duplicate_chunk_count: int
    warnings: list[str]
    errors: list[str]
    reports: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_project_path(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return PROJECT_DIR / candidate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def content_hash(text: str) -> str:
    normalized = normalize_text(text or "")
    return hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()


def _stable_id(*parts: object, size: int = 16) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:size]


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return asdict(value)
    return str(value)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=_json_default))
            handle.write("\n")
            count += 1
    return count


def _quality_payload(quality: PageExtractionQuality) -> dict[str, Any]:
    payload = asdict(quality)
    payload["has_equations"] = quality.has_equation_like_text
    return payload


def _page_payload(page: ExtractedSolutionPage) -> dict[str, Any]:
    payload = asdict(page)
    payload["quality"] = _quality_payload(page.quality)
    if page.status.startswith("blocked"):
        payload["extraction_method"] = "blocked"
    return payload


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _database_backend_label() -> str:
    url = settings.resolved_database_url
    if url.startswith("postgres"):
        return "postgresql_pgvector"
    if url.startswith("sqlite"):
        return "sqlite_json_embedding_dev"
    return "sqlalchemy_vector_store"


def _arabic_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    arabic = sum(1 for char in letters if _ARABIC_RE.match(char))
    return round(arabic / len(letters), 4)


def _weird_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    allowed = 0
    for char in text:
        if char.isspace() or char.isalnum() or _ARABIC_RE.match(char):
            allowed += 1
        elif char in ".,;:!?؟،؛()[]{}+-=*/\\|_%٪°<>→⟶⇌←↔'\"`~^&\n\r\t":
            allowed += 1
    return round(1 - (allowed / max(len(text), 1)), 4)


def write_audit_report(
    *,
    output_dir: Path,
    pdf_path: Path,
    source_file_hash: str,
    document_id: str,
) -> Path:
    """Write a concise codebase audit for solution-book ingestion."""
    provider = get_vision_provider(None)
    embedding_status = embedding_provider_status()
    report_path = output_dir / "audit_report.md"
    lines = [
        "# Solution Book Ingestion Audit",
        "",
        f"- Generated at: {datetime.now(timezone.utc).isoformat()}",
        f"- Solution PDF: `{pdf_path}`",
        f"- Document ID: `{document_id}`",
        f"- Source type: `{SOURCE_TYPE}`",
        f"- Source file hash: `{source_file_hash}`",
        "",
        "## Existing PDF Extraction Flow",
        "",
        "- Digital text extraction uses `app.services.pdf_processor.extract_text_page`, backed by PyMuPDF and pdfplumber.",
        "- Visual detection uses `detect_visual_content` with image area, table detection, and equation hints.",
        "- Vision/OCR fallback uses the provider returned by `app.services.ocr.get_vision_provider`.",
        f"- Current OCR/Vision provider: `{provider.name}`; configured: `{provider.is_configured}`.",
        f"- Gemini document model: `{settings.gemini_document_model}`.",
        f"- Gemini document fallback model: `{settings.gemini_document_fallback_model}`.",
        "",
        "## Existing RAG And Vector System",
        "",
        f"- Embedding provider config: `{embedding_status.get('provider')}`.",
        f"- Gemini embedding model: `{settings.gemini_embedding_model}`.",
        f"- Local embedding model: `{settings.local_embedding_model}`.",
        f"- Embedding dimension: `{EMBEDDING_DIM}`.",
        f"- Vector storage backend for current settings: `{_database_backend_label()}`.",
        "- Production PostgreSQL uses `rag_chunks.embedding` as pgvector when the database URL is PostgreSQL and pgvector is installed.",
        "- SQLite development mode stores embeddings as JSON for local smoke tests.",
        "",
        "## Existing Database Models",
        "",
        "- `content_sources` stores source metadata including `source_type`, file path, status, and `metadata_json`.",
        "- `rag_chunks` stores chunk text, normalized text, source/page metadata, embeddings, content type, and `source_type`.",
        "- `extracted_questions` can store extracted exercise/question payloads for future quiz workflows.",
        "",
        "## API Surface",
        "",
        "- Admin solution-book ingestion is exposed through `POST /api/v1/admin/ingestion/solution-book`.",
        "- Alias route is exposed through `POST /api/v1/admin/ingest/solution-book`.",
        "- Semantic RAG search is exposed through `/api/v1/rag/search`.",
        "",
        "## Problems Addressed By This Pipeline",
        "",
        "- Solution-book chunks are stored with `source_type=solution_book`, so textbook chunks are not overwritten.",
        "- Re-ingestion is idempotent through `source_file_hash` and per-chunk `content_hash` metadata.",
        "- Production ingestion refuses to complete with blocked OCR/Vision pages unless partial ingestion is explicitly enabled.",
        "- Generated JSONL/JSON reports make extraction, chunking, embedding, and DB writes inspectable.",
    ]
    _write_text(report_path, "\n".join(lines) + "\n")
    return report_path


def evaluate_page_text_quality(
    text: str,
    *,
    page_number: int,
    visual_info: dict[str, Any] | None = None,
) -> PageExtractionQuality:
    visual = visual_info or {}
    stripped = (text or "").strip()
    text_length = len(stripped)
    line_count = len([line for line in stripped.splitlines() if line.strip()])
    arabic_ratio = _arabic_ratio(stripped)
    weird_ratio = _weird_char_ratio(stripped)
    has_images = bool(visual.get("image_count", 0) > 0 or visual.get("has_images"))
    has_tables = bool(visual.get("table_count", 0) > 0 or visual.get("has_tables"))
    has_equation_like_text = bool(visual.get("has_equation_hints") or _EQUATION_HINT_RE.search(stripped))

    issues: list[str] = []
    if text_length < 100:
        issues.append(f"low_text_length:{text_length}")
    if weird_ratio > 0.15:
        issues.append(f"weird_char_ratio:{weird_ratio:.2f}")
    if stripped and arabic_ratio < 0.2:
        issues.append(f"low_arabic_ratio:{arabic_ratio:.2f}")
    image_area_ratio = float(visual.get("image_area_ratio") or 0.0)
    if has_images and image_area_ratio > 0.35 and text_length < 350:
        issues.append(f"image_heavy_page:{image_area_ratio:.2f}")
    has_usable_structured_text = text_length >= 300 and line_count >= 3 and arabic_ratio >= 0.5 and weird_ratio <= 0.12
    table_needs_vision = has_tables and not has_usable_structured_text and (
        text_length < 700 or weird_ratio > 0.12 or (stripped and arabic_ratio < 0.2)
    )
    if has_tables:
        issues.append("table_detected" if table_needs_vision else "table_detected_digital_text_usable")
    if has_equation_like_text and text_length < 220:
        issues.append("sparse_equation_page")

    needs_ocr = any(issue.startswith(("low_text_length", "weird_char_ratio", "low_arabic_ratio")) for issue in issues)
    needs_vision = table_needs_vision or "sparse_equation_page" in issues or any(
        issue.startswith("image_heavy_page") for issue in issues
    )
    penalty = 0.0
    if needs_ocr:
        penalty += 0.35
    if needs_vision:
        penalty += 0.25
    if weird_ratio > 0:
        penalty += min(weird_ratio, 0.25)
    confidence = round(max(0.0, min(1.0, 1.0 - penalty)), 4)
    return PageExtractionQuality(
        page_number=page_number,
        text_length=text_length,
        arabic_ratio=arabic_ratio,
        weird_char_ratio=weird_ratio,
        line_count=line_count,
        has_equation_like_text=has_equation_like_text,
        has_images=has_images,
        has_tables=has_tables,
        needs_ocr=needs_ocr,
        needs_vision=needs_vision,
        confidence=confidence,
        issues=issues,
    )


def _vision_payload_to_text(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    parts.append(str(payload.get("raw_markdown") or payload.get("raw_text") or "").strip())
    for section in payload.get("sections") or []:
        heading = str(section.get("heading") or section.get("title") or "").strip()
        content = str(section.get("content") or "").strip()
        parts.append("\n".join(part for part in (heading, content) if part))
    for question in payload.get("questions") or []:
        parts.append(str(question.get("question_text") or "").strip())
        if question.get("explanation"):
            parts.append(str(question["explanation"]).strip())
    for table in payload.get("tables") or []:
        parts.append(str(table.get("markdown") or "").strip())
    for equation in payload.get("equations") or []:
        parts.append(str(equation.get("equation") or "").strip())
    for diagram in payload.get("diagrams") or []:
        parts.append(str(diagram.get("description") or "").strip())
    return "\n\n".join(part for part in parts if part)


def _extract_solution_selectable_text(pdf_path: Path, page_number: int) -> tuple[str, str]:
    """Prefer clean PyMuPDF text; use pdfplumber tables only for sparse pages."""
    import fitz

    doc = fitz.open(pdf_path)
    try:
        primary_text = doc[page_number - 1].get_text("text") or ""
    finally:
        doc.close()
    if len(primary_text.strip()) >= 300 and _arabic_ratio(primary_text) >= 0.2:
        return primary_text, "pymupdf_text"
    return extract_text_page(str(pdf_path), page_number), "pymupdf_pdfplumber_tables"


async def extract_solution_book_pages(
    pdf_path: Path,
    *,
    document_id: str,
    source_file_hash: str,
    output_dir: Path,
    mode: str,
    use_ocr: bool,
    use_vision: bool,
    ocr_provider_name: str | None,
    max_pages: int | None = None,
) -> tuple[list[ExtractedSolutionPage], dict[str, Any]]:
    """Extract solution-book pages and write ``pages.jsonl``."""
    import fitz

    provider = get_vision_provider(ocr_provider_name)
    pages: list[ExtractedSolutionPage] = []
    warnings: list[str] = []
    errors: list[str] = []
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    pages_to_process = min(total_pages, max_pages) if max_pages else total_pages
    image_dir = output_dir / "page_images"
    uploaded_pdf = None
    upload_attempted = False

    for page_number in range(1, pages_to_process + 1):
        page_warnings: list[str] = []
        page_errors: list[str] = []
        page_image_path: str | None = None
        visual = detect_visual_content(str(pdf_path), page_number)
        text, selectable_text_source = _extract_solution_selectable_text(pdf_path, page_number)
        quality = evaluate_page_text_quality(text, page_number=page_number, visual_info=visual)
        extraction_method = "digital_text"
        status = "extracted"

        should_use_vision = use_vision and quality.needs_vision
        should_use_ocr = use_ocr and quality.needs_ocr
        if should_use_vision or should_use_ocr:
            if provider.is_configured:
                vision_text = ""
                if settings.pdf_direct_extraction_enabled:
                    try:
                        if not upload_attempted:
                            upload_attempted = True
                            uploaded_pdf = await provider.upload_pdf(str(pdf_path))
                        if uploaded_pdf is not None:
                            vision_result = await provider.extract_page_from_pdf(
                                uploaded_pdf,
                                page_number,
                                SOURCE_TYPE,
                                neighboring_pages=[p for p in (page_number - 1, page_number + 1) if 1 <= p <= total_pages],
                            )
                            vision_text = _vision_payload_to_text(vision_result.to_payload())
                    except NotImplementedError:
                        page_warnings.append("Provider does not support direct PDF extraction; using image fallback.")
                    except Exception as exc:  # pragma: no cover - external provider
                        page_warnings.append(f"direct_pdf_extraction_failed:{exc}")

                if not vision_text.strip() and settings.pdf_image_fallback_enabled:
                    try:
                        image_path = render_page_to_image(str(pdf_path), page_number, image_dir, dpi=300)
                        page_image_path = str(image_path)
                        vision_result = await provider.extract_page(str(image_path), page_number, SOURCE_TYPE)
                        vision_text = _vision_payload_to_text(vision_result.to_payload())
                    except Exception as exc:  # pragma: no cover - external provider
                        page_errors.append(f"vision_image_fallback_failed:{exc}")

                if vision_text.strip():
                    text = "\n\n".join(part for part in (text.strip(), vision_text.strip()) if part)
                    extraction_method = "mixed" if quality.text_length >= 100 else "vision"
                    quality = evaluate_page_text_quality(text, page_number=page_number, visual_info=visual)
                else:
                    page_warnings.append("Vision/OCR provider returned no usable text; page remains blocked.")
                    status = "blocked_vision_required" if mode == "production" else "blocked_dry_run"
            else:
                status = "blocked_vision_required" if mode == "production" else "blocked_dry_run"
                provider_kind = "Vision" if should_use_vision else "OCR"
                page_warnings.append(f"{provider_kind} required but provider is not configured.")

        normalized = normalize_text(text)
        if status.startswith("blocked") and quality.text_length >= 250 and not quality.needs_ocr and mode == "dry_run":
            page_warnings.append("Dry-run kept readable digital text, but page is not production-complete.")

        page = ExtractedSolutionPage(
            document_id=document_id,
            source_type=SOURCE_TYPE,
            page_number=page_number,
            text=text,
            normalized_text=normalized,
            extraction_method=extraction_method,
            quality=quality,
            images=[
                {
                    "image_count": visual.get("image_count", 0),
                    "image_area_ratio": visual.get("image_area_ratio", 0.0),
                    "page_image_path": page_image_path,
                }
            ],
            metadata={
                "source_file": str(pdf_path),
                "source_file_path": str(pdf_path),
                "source_file_hash": source_file_hash,
                "page_image_path": page_image_path,
                "selectable_text_source": selectable_text_source,
                "visual": visual,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
            status=status,
            warnings=page_warnings,
            errors=page_errors,
        )
        pages.append(page)
        warnings.extend(f"page {page_number}: {item}" for item in page_warnings)
        errors.extend(f"page {page_number}: {item}" for item in page_errors)

    pages_path = output_dir / "pages.jsonl"
    _write_jsonl(pages_path, [_page_payload(page) for page in pages])
    blocked_page_numbers = [page.page_number for page in pages if page.status.startswith("blocked")]
    low_quality_pages = [
        {
            "page_number": page.page_number,
            "confidence": page.quality.confidence,
            "issues": page.quality.issues,
        }
        for page in pages
        if page.quality.confidence < 0.6 or page.quality.needs_ocr or page.quality.needs_vision
    ]
    quality_scores = [page.quality.confidence for page in pages]
    report = {
        "pdf_path": str(pdf_path),
        "source_file_hash": source_file_hash,
        "total_pages": total_pages,
        "pages_processed": pages_to_process,
        "digital_text_pages": sum(1 for page in pages if page.extraction_method == "digital_text"),
        "ocr_pages": sum(1 for page in pages if page.extraction_method == "ocr"),
        "vision_pages": sum(1 for page in pages if page.extraction_method == "vision"),
        "mixed_pages": sum(1 for page in pages if page.extraction_method == "mixed"),
        "pages_extracted_digitally": sum(1 for page in pages if page.extraction_method == "digital_text"),
        "pages_needing_ocr": [page.page_number for page in pages if page.quality.needs_ocr],
        "pages_needing_vision": [page.page_number for page in pages if page.quality.needs_vision],
        "blocked_pages": len(blocked_page_numbers),
        "blocked_page_numbers": blocked_page_numbers,
        "low_quality_pages": low_quality_pages,
        "average_quality_score": round(mean(quality_scores), 4) if quality_scores else 0.0,
        "provider_used": provider.name,
        "provider_configured": provider.is_configured,
        "warnings": warnings,
        "errors": errors,
        "pages_jsonl": str(pages_path),
    }
    _write_json(output_dir / "extraction_report.json", report)
    missing_requirements: list[str] = []
    if (use_ocr or use_vision) and not provider.is_configured:
        missing_requirements.append("GEMINI_API_KEY or GOOGLE_API_KEY")
    ocr_review_report = {
        "ocr_available": provider.is_configured,
        "vision_available": provider.is_configured,
        "provider_used": provider.name,
        "reviewed_pages": [
            page.page_number for page in pages if page.quality.needs_ocr or page.quality.needs_vision
        ],
        "ocr_pages": [page.page_number for page in pages if page.extraction_method == "ocr"],
        "vision_pages": [page.page_number for page in pages if page.extraction_method == "vision"],
        "mixed_pages": [page.page_number for page in pages if page.extraction_method == "mixed"],
        "blocked_pages": blocked_page_numbers,
        "missing_requirements": missing_requirements,
        "warnings": warnings,
        "errors": errors,
    }
    _write_json(output_dir / "ocr_review_report.json", ocr_review_report)
    return pages, report


def _extract_lesson_title(text: str) -> str | None:
    match = _LESSON_RE.search(text or "")
    return " ".join(match.group(0).split())[:120] if match else None


def _extract_chapter_title(text: str) -> str | None:
    match = _CHAPTER_RE.search(text or "")
    return " ".join(match.group(0).split())[:120] if match else None


def _extract_question_number(text: str) -> str | None:
    match = _QUESTION_NO_RE.search(text or "")
    if not match:
        return None
    number = match.group(1)
    return number.strip() if number else None


def _split_question_solution(text: str) -> tuple[str | None, str]:
    parts = re.split(r"\n?\s*(?:الحل|حل|الإجابة|اجابة)\s*[:：]", text, maxsplit=1)
    if len(parts) == 2:
        question = parts[0].strip() or None
        solution = parts[1].strip()
        return question, solution or text.strip()
    return None, text.strip()


def _solution_steps(text: str) -> list[str]:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    steps = [
        line
        for line in lines
        if re.search(r"(?:الخطوة|خطوة)\s*\d+|(?:^\d+[.)-]\s)|=", line)
    ]
    return steps[:20]


def _equations(text: str) -> list[str]:
    equations = [line.strip() for line in (text or "").splitlines() if _EQUATION_LINE_RE.match(line.strip())]
    if equations:
        return equations[:20]
    return extract_formula_terms(text)[:20]


def _final_answer(text: str) -> str | None:
    for line in reversed([line.strip() for line in (text or "").splitlines() if line.strip()]):
        match = _FINAL_ANSWER_RE.search(line)
        if match:
            return match.group(1).strip() or line
    return None


def _related_pages(text: str) -> list[int]:
    pages: set[int] = set()
    for match in _PAGE_REF_RE.finditer(text or ""):
        raw = normalize_text(match.group(1))
        try:
            pages.add(int(raw))
        except ValueError:
            continue
    return sorted(page for page in pages if 1 <= page <= 300)


def _keywords(text: str) -> list[str]:
    normalized = normalize_text(text)
    formulas = extract_formula_terms(text)
    selected_terms = []
    for term in (
        "تركيز",
        "مولي",
        "غرامي",
        "حمض",
        "اساس",
        "ملح",
        "تفاعل",
        "معادله",
        "كربونات",
        "هيدروكسيد",
    ):
        if term in normalized:
            selected_terms.append(term)
    return sorted(set([*formulas, *selected_terms]))[:24]


def parse_solution_units(
    pages: list[ExtractedSolutionPage],
    *,
    document_id: str,
    output_dir: Path,
) -> list[SolutionUnit]:
    """Parse page text into solution-aware logical units."""
    units: list[SolutionUnit] = []
    current_chapter: str | None = None
    current_lesson: str | None = None

    for page in pages:
        if page.status.startswith("blocked") or not page.text.strip():
            continue
        page_chapter = _extract_chapter_title(page.text)
        page_lesson = _extract_lesson_title(page.text)
        current_chapter = page_chapter or current_chapter
        current_lesson = page_lesson or current_lesson
        starts = [match.start() for match in _UNIT_START_RE.finditer(page.text)]
        if not starts:
            raw_units = [page.text.strip()]
        else:
            raw_units = []
            starts.append(len(page.text))
            for start, end in zip(starts, starts[1:]):
                unit_text = page.text[start:end].strip()
                if unit_text:
                    raw_units.append(unit_text)

        for unit_index, raw_unit in enumerate(raw_units):
            question_text, solution_text = _split_question_solution(raw_unit)
            if len(solution_text.strip()) < 20:
                continue
            question_number = _extract_question_number(raw_unit)
            unit = SolutionUnit(
                id="sol_unit_" + _stable_id(document_id, page.page_number, unit_index, raw_unit),
                document_id=document_id,
                source_type=SOURCE_TYPE,
                chapter_title=current_chapter,
                lesson_title=current_lesson,
                page_number=page.page_number,
                exercise_number=question_number,
                question_number=question_number,
                question_text=question_text,
                solution_text=solution_text,
                solution_steps=_solution_steps(solution_text),
                final_answer=_final_answer(solution_text),
                equations=_equations(solution_text),
                keywords=_keywords(raw_unit),
                related_textbook_pages=_related_pages(raw_unit),
                extraction_confidence=page.quality.confidence,
            )
            units.append(unit)

    path = output_dir / "solution_units.jsonl"
    _write_jsonl(path, [asdict(unit) for unit in units])
    units_with_detected_question_number = [unit.id for unit in units if unit.question_number]
    units_with_detected_equations = [unit.id for unit in units if unit.equations]
    units_missing_question_text = [unit.id for unit in units if not unit.question_text]
    units_with_low_confidence = [
        {"id": unit.id, "page_number": unit.page_number, "confidence": unit.extraction_confidence}
        for unit in units
        if unit.extraction_confidence < 0.6
    ]
    _write_json(
        output_dir / "solution_units_report.json",
        {
            "total_units": len(units),
            "solution_units": len(units),
            "units_with_detected_question_number": len(units_with_detected_question_number),
            "units_with_detected_equations": len(units_with_detected_equations),
            "units_missing_question_text": len(units_missing_question_text),
            "units_with_low_confidence": len(units_with_low_confidence),
            "low_confidence_units": units_with_low_confidence,
            "pages_with_units": sorted({unit.page_number for unit in units}),
            "units_jsonl": str(path),
        },
    )
    return units


def _chunk_type_for_record(record: ChunkRecord, unit: SolutionUnit) -> str:
    if record.content_type == "equation" or _EQUATION_LINE_RE.search(record.content):
        return "equation"
    if record.content_type in {"solution_step", "final_answer"} or re.search(r"(?:Cm|C|n|m|V|M)\s*=", record.content):
        return "calculation"
    if record.content_type in {"exercise_question", "exercise_solution"}:
        return "exercise_answer"
    if "تعريف" in normalize_text(record.content):
        return "definition"
    if unit.question_text:
        return "solution"
    return "mixed"


def _bad_chunk_ending_reason(content: str) -> str | None:
    stripped = (content or "").strip()
    if not stripped:
        return "empty_content"
    last_line = stripped.splitlines()[-1].strip()
    if _EQUATION_LINE_RE.match(last_line):
        return None
    if stripped[-1] in ".؟!؛:":
        return None
    if stripped[-1] in ",،-/+":
        return "dangling_punctuation"
    if re.search(r"\b(?:و|أو|ثم|حيث|لأن|عند|من|إلى|في|على)\s*$", normalize_text(stripped)):
        return "dangling_arabic_connector"
    if len(stripped) > 250:
        return "no_sentence_terminal"
    return None


def build_solution_book_chunks(
    units: list[SolutionUnit],
    *,
    document_id: str,
    source_pdf: str,
    output_dir: Path,
) -> tuple[list[SolutionBookChunk], dict[str, Any]]:
    """Create sentence-aware RAG chunks from solution units."""
    chunks: list[SolutionBookChunk] = []
    seen_hashes: set[str] = set()
    duplicate_count = 0
    warnings: list[str] = []
    bad_endings: list[dict[str, Any]] = []

    for unit in units:
        content_parts = []
        if unit.question_text:
            content_parts.append(f"السؤال:\n{unit.question_text}")
        content_parts.append(f"الحل:\n{unit.solution_text}")
        if unit.final_answer:
            content_parts.append(f"الجواب النهائي:\n{unit.final_answer}")
        unit_content = "\n\n".join(part.strip() for part in content_parts if part.strip())

        records = split_solution_book_text(
            unit_content,
            max_chars=1200,
            page_number=unit.page_number,
            document_id=document_id,
            source_pdf=source_pdf,
        )
        for split_index, record in enumerate(records):
            hash_value = content_hash(record.content)
            if hash_value in seen_hashes:
                duplicate_count += 1
                continue
            seen_hashes.add(hash_value)
            bad_ending_reason = _bad_chunk_ending_reason(record.content)
            if bad_ending_reason:
                bad_endings.append(
                    {
                        "unit_id": unit.id,
                        "split_index": split_index,
                        "reason": bad_ending_reason,
                        "preview": record.content[-120:],
                    }
                )
                warnings.append(f"chunk may end mid-sentence: unit={unit.id} split={split_index}")
            chunk_type = _chunk_type_for_record(record, unit)
            chunk = SolutionBookChunk(
                id="sol_chunk_" + _stable_id(unit.id, split_index, hash_value),
                document_id=document_id,
                source_type=SOURCE_TYPE,
                chunk_type=chunk_type,
                chapter_title=unit.chapter_title,
                lesson_title=unit.lesson_title,
                page_start=unit.page_number,
                page_end=unit.page_number,
                exercise_number=unit.exercise_number,
                question_number=unit.question_number,
                content=record.content,
                content_ar=record.content,
                keywords=sorted(set([*unit.keywords, *extract_formula_terms(record.content)]))[:30],
                equations=_equations(record.content) or unit.equations,
                metadata={
                    **record.metadata,
                    "unit_id": unit.id,
                    "content_hash": hash_value,
                    "chunk_hash": hash_value,
                    "source_type": SOURCE_TYPE,
                    "page_start": unit.page_number,
                    "page_end": unit.page_number,
                    "chapter_title": unit.chapter_title,
                    "lesson_title": unit.lesson_title,
                    "exercise_number": unit.exercise_number,
                    "question_number": unit.question_number,
                    "related_textbook_pages": unit.related_textbook_pages,
                    "quality_score": unit.extraction_confidence,
                    "extraction_confidence": unit.extraction_confidence,
                },
            )
            chunks.append(chunk)

    chunks_path = output_dir / "chunks.jsonl"
    _write_jsonl(chunks_path, [asdict(chunk) for chunk in chunks])
    lengths = [len(chunk.content) for chunk in chunks]
    chunks_with_question_number = [chunk.id for chunk in chunks if chunk.question_number]
    chunks_with_equations = [chunk.id for chunk in chunks if chunk.equations]
    chunks_by_type = dict(Counter(chunk.chunk_type for chunk in chunks))
    report = {
        "total_chunks": len(chunks),
        "chunks": len(chunks),
        "average_chunk_chars": round(mean(lengths), 2) if lengths else 0.0,
        "min_chunk_chars": min(lengths) if lengths else 0,
        "max_chunk_chars": max(lengths) if lengths else 0,
        "average_chunk_length": round(mean(lengths), 2) if lengths else 0.0,
        "min_chunk_length": min(lengths) if lengths else 0,
        "max_chunk_length": max(lengths) if lengths else 0,
        "chunks_by_type": chunks_by_type,
        "chunks_with_question_number": len(chunks_with_question_number),
        "chunks_with_equations": len(chunks_with_equations),
        "duplicate_chunks": duplicate_count,
        "duplicate_chunk_count": duplicate_count,
        "bad_endings": bad_endings,
        "content_type_counts": chunks_by_type,
        "warnings": warnings,
        "chunks_jsonl": str(chunks_path),
    }
    _write_json(output_dir / "chunking_report.json", report)
    return chunks, report


async def _embed_with_retries(texts: list[str], *, retries: int = 3) -> list[list[float]]:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            return await embed_batch(texts)
        except Exception as exc:  # pragma: no cover - provider/network dependent
            last_exc = exc
            await asyncio.sleep(0.25 * (2**attempt))
    raise RuntimeError(f"Embedding failed after {retries} attempts: {last_exc}") from last_exc


def _get_or_create_solution_source(
    db: Session,
    *,
    pdf_path: Path,
    document_id: str,
    title: str,
    source_file_hash: str,
    force_reingest: bool,
) -> tuple[ContentSource, bool, bool]:
    path = str(pdf_path)
    source = (
        db.query(ContentSource)
        .filter(ContentSource.source_type == SOURCE_TYPE, ContentSource.file_path == path)
        .first()
    )
    if source is None:
        source = (
            db.query(ContentSource)
            .filter(ContentSource.source_type == SOURCE_TYPE, ContentSource.title == title)
            .first()
        )
    file_changed = False
    if source is None:
        created_source = True
        source = ContentSource(
            source_type=SOURCE_TYPE,
            title=title,
            grade="grade_9",
            subject="chemistry",
            file_path=path,
            original_filename=pdf_path.name,
            status="processing",
            metadata_json={
                "document_id": document_id,
                "document_type": SOURCE_TYPE,
                "source_file_hash": source_file_hash,
            },
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    else:
        created_source = False
        previous_hash = (source.metadata_json or {}).get("source_file_hash")
        file_changed = bool(previous_hash and previous_hash != source_file_hash)
        source.status = "processing"
        source.file_path = path
        source.original_filename = pdf_path.name
        metadata = dict(source.metadata_json or {})
        metadata.update(
            {
                "document_id": document_id,
                "document_type": SOURCE_TYPE,
                "source_file_hash": source_file_hash,
            }
        )
        source.metadata_json = metadata
        if force_reingest or file_changed:
            db.query(RagChunk).filter(RagChunk.source_id == source.id).delete(synchronize_session=False)
        db.commit()
        db.refresh(source)
    return source, file_changed, created_source


async def store_solution_book_chunks(
    db: Session,
    *,
    source: ContentSource,
    chunks: list[SolutionBookChunk],
    source_file_hash: str,
    force_reingest: bool,
) -> dict[str, Any]:
    """Embed and store solution chunks idempotently."""
    reviewed_metadata = ensure_reviewed_metadata_ready()
    if force_reingest:
        db.query(RagChunk).filter(RagChunk.source_id == source.id).delete(synchronize_session=False)
        db.commit()

    existing_rows = db.query(RagChunk).filter(RagChunk.source_id == source.id).all()
    existing_hashes = {
        str((row.metadata_json or {}).get("content_hash"))
        for row in existing_rows
        if isinstance(row.metadata_json, dict) and (row.metadata_json or {}).get("content_hash")
    }
    duplicate_skipped = len([chunk for chunk in chunks if chunk.metadata.get("content_hash") in existing_hashes])
    missing_metadata_skips: list[dict[str, Any]] = []
    blocked_skips: list[dict[str, Any]] = []
    to_insert: list[SolutionBookChunk] = []
    for chunk in chunks:
        if chunk.metadata.get("content_hash") in existing_hashes:
            continue
        candidate = {
            **(chunk.metadata or {}),
            "content": chunk.content,
            "source_type": chunk.source_type,
            "printed_page_start": chunk.metadata.get("printed_page_start"),
            "printed_page_end": chunk.metadata.get("printed_page_end"),
            "quality_status": chunk.metadata.get("quality_status"),
        }
        ready, reason, missing = chunk_is_embedding_ready(candidate, reviewed_metadata)
        if ready:
            to_insert.append(chunk)
        elif reason == "blocked_quality_status":
            blocked_skips.append({"chunk_id": chunk.id, "reason": reason})
        else:
            missing_metadata_skips.append(
                {"chunk_id": chunk.id, "reason": reason, "missing_metadata": missing}
            )
    skipped = len(chunks) - len(to_insert)
    failed: list[dict[str, Any]] = []
    errors: list[str] = []

    batch_size = 64
    inserted = 0
    for start in range(0, len(to_insert), batch_size):
        batch = to_insert[start : start + batch_size]
        try:
            embeddings = await _embed_with_retries([chunk.content for chunk in batch])
        except Exception as exc:  # pragma: no cover - provider/network dependent
            failed.extend({"chunk_id": chunk.id, "error": str(exc)} for chunk in batch)
            errors.append(str(exc))
            continue
        for offset, (chunk, embedding) in enumerate(zip(batch, embeddings), start=start):
            db.add(
                RagChunk(
                    source_id=source.id,
                    chapter_id=None,
                    lesson_id=None,
                    topic_id=None,
                    page_number=chunk.page_start,
                    chunk_index=len(existing_rows) + offset,
                    content=chunk.content,
                    normalized_content=normalize_text(chunk.content),
                    content_type=chunk.chunk_type,
                    source_type=SOURCE_TYPE,
                    extraction_method=str(chunk.metadata.get("extraction_method") or "solution_book_pipeline"),
                    language="ar",
                    embedding=embedding,
                    embedding_model=current_embedding_model_name(),
                    embedding_updated_at=datetime.now(timezone.utc),
                    metadata_json={
                        **metadata_with_reviewed_version(chunk.metadata, reviewed_metadata),
                        "document_id": chunk.document_id,
                        "document_type": SOURCE_TYPE,
                        "source_file_hash": source_file_hash,
                        "embedding_model": current_embedding_model_name(),
                        "embedding_provider": embedding_provider_status(),
                        "embedding_dimension": EMBEDDING_DIM,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            )
            inserted += 1
        db.commit()

    provider_status = embedding_provider_status()
    return {
        "embedding_model": provider_status.get("gemini_model") or provider_status.get("local_model"),
        "embedding_dimension": EMBEDDING_DIM,
        "chunks_to_embed": len(to_insert),
        "embedded_chunks": inserted,
        "skipped_existing": duplicate_skipped,
        "skipped_missing_metadata_count": len(missing_metadata_skips),
        "skipped_blocked_count": len(blocked_skips),
        "skipped_missing_metadata": missing_metadata_skips[:50],
        "skipped_blocked": blocked_skips[:50],
        "reviewed_metadata_version": reviewed_metadata.get("version"),
        "metadata_ready": True,
        "skipped_total": skipped,
        "failed_chunks": failed,
        "errors": errors,
        "chunks_total": len(chunks),
        "chunks_inserted": inserted,
        "chunks_skipped_duplicate": skipped,
        "embedding_provider": provider_status,
    }


def _ingestion_report(
    *,
    pages: list[ExtractedSolutionPage],
    units: list[SolutionUnit],
    chunks: list[SolutionBookChunk],
    extraction_report: dict[str, Any],
    chunking_report: dict[str, Any],
    embedding_report: dict[str, Any] | None,
    mode: str,
    source_file_hash: str,
) -> dict[str, Any]:
    lengths = [len(chunk.content) for chunk in chunks]
    blocked = [page.page_number for page in pages if page.status.startswith("blocked")]
    return {
        "mode": mode,
        "source_type": SOURCE_TYPE,
        "source_file_hash": source_file_hash,
        "number_of_pages": len(pages),
        "pages_extracted_digitally": sum(1 for page in pages if page.extraction_method == "digital_text"),
        "pages_needing_ocr": len([page for page in pages if page.quality.needs_ocr]),
        "pages_needing_vision": len([page for page in pages if page.quality.needs_vision]),
        "blocked_pages": blocked,
        "number_of_solution_units": len(units),
        "number_of_chunks": len(chunks),
        "average_chunk_length": round(mean(lengths), 2) if lengths else 0.0,
        "min_chunk_length": min(lengths) if lengths else 0,
        "max_chunk_length": max(lengths) if lengths else 0,
        "duplicate_chunk_count": int(chunking_report.get("duplicate_chunk_count") or 0),
        "extraction_warnings": extraction_report.get("warnings") or [],
        "chunking_warnings": chunking_report.get("warnings") or [],
        "embedding_report": embedding_report or {},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def ingest_solution_book(
    *,
    file_path: str | Path = DEFAULT_PDF_PATH,
    mode: str = "dry_run",
    force_reingest: bool = False,
    use_ocr: bool = True,
    use_vision: bool = True,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    document_id: str = DEFAULT_DOCUMENT_ID,
    title: str = DEFAULT_TITLE,
    max_pages: int | None = None,
    ocr_provider_name: str | None = None,
    allow_partial: bool | None = None,
    db: Session | None = None,
) -> SolutionBookIngestionResult:
    """Run the complete solution-book ingestion pipeline."""
    resolved_mode = (mode or "dry_run").strip().lower()
    if resolved_mode not in {"dry_run", "production"}:
        raise ValueError("mode must be either 'dry_run' or 'production'")

    pdf_path = resolve_project_path(file_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"Solution book PDF not found: {pdf_path}")
    out_dir = resolve_project_path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    source_file_hash = sha256_file(pdf_path)
    audit_report_path = write_audit_report(
        output_dir=out_dir,
        pdf_path=pdf_path,
        source_file_hash=source_file_hash,
        document_id=document_id,
    )
    logger.info("Starting solution book ingestion: %s mode=%s", pdf_path, resolved_mode)

    pages, extraction_report = await extract_solution_book_pages(
        pdf_path,
        document_id=document_id,
        source_file_hash=source_file_hash,
        output_dir=out_dir,
        mode=resolved_mode,
        use_ocr=use_ocr,
        use_vision=use_vision,
        ocr_provider_name=ocr_provider_name,
        max_pages=max_pages,
    )
    units = parse_solution_units(pages, document_id=document_id, output_dir=out_dir)
    chunks, chunking_report = build_solution_book_chunks(
        units,
        document_id=document_id,
        source_pdf=pdf_path.name,
        output_dir=out_dir,
    )

    blocked_pages = [page.page_number for page in pages if page.status.startswith("blocked")]
    embedding_report: dict[str, Any] | None = None
    db_ingestion_report: dict[str, Any] = {
        "mode": resolved_mode,
        "source_type": SOURCE_TYPE,
        "db_table": "rag_chunks",
        "vector_store": _database_backend_label(),
        "inserted_documents": 0,
        "updated_documents": 0,
        "inserted_chunks": 0,
        "updated_chunks": 0,
        "skipped_chunks": 0,
        "inserted_embeddings": 0,
        "skipped_embeddings": 0,
        "failed_chunks": [],
        "errors": [],
    }
    source_id: int | None = None
    errors: list[str] = list(extraction_report.get("errors") or [])
    warnings: list[str] = [
        *list(extraction_report.get("warnings") or []),
        *list(chunking_report.get("warnings") or []),
    ]

    owns_db = db is None
    session = db or SessionLocal()
    try:
        if resolved_mode == "production":
            resolved_allow_partial = (
                settings.allow_partial_solution_book_ingestion if allow_partial is None else allow_partial
            )
            if blocked_pages and not resolved_allow_partial:
                raise RuntimeError(
                    "Cannot run production solution-book ingestion with blocked pages: "
                    + ", ".join(map(str, blocked_pages))
                    + ". Set ALLOW_PARTIAL_SOLUTION_BOOK_INGESTION=true only if partial ingestion is intentional."
                )
            if not chunks:
                raise RuntimeError("Cannot run production solution-book ingestion because no chunks were produced.")
            source, file_changed, created_source = _get_or_create_solution_source(
                session,
                pdf_path=pdf_path,
                document_id=document_id,
                title=title,
                source_file_hash=source_file_hash,
                force_reingest=force_reingest,
            )
            source_id = source.id
            if file_changed:
                warnings.append("PDF file hash changed; refreshed existing solution_book chunks for this source.")
            embedding_report = await store_solution_book_chunks(
                session,
                source=source,
                chunks=chunks,
                source_file_hash=source_file_hash,
                force_reingest=force_reingest,
            )
            source.status = "completed" if not embedding_report.get("failed_chunks") else "completed_with_warnings"
            metadata = dict(source.metadata_json or {})
            metadata.update(
                {
                    "document_id": document_id,
                    "document_type": SOURCE_TYPE,
                    "source_file_hash": source_file_hash,
                    "processed_output_dir": str(out_dir),
                    "pages": len(pages),
                    "solution_units": len(units),
                    "chunks": len(chunks),
                    "embedding_report": embedding_report,
                }
            )
            source.metadata_json = metadata
            session.commit()
            db_ingestion_report.update(
                {
                    "source_id": source.id,
                    "inserted_documents": 1 if created_source else 0,
                    "updated_documents": 0 if created_source else 1,
                    "inserted_chunks": int(embedding_report.get("chunks_inserted") or 0),
                    "updated_chunks": 0,
                    "skipped_chunks": int(embedding_report.get("chunks_skipped_duplicate") or 0),
                    "inserted_embeddings": int(embedding_report.get("embedded_chunks") or 0),
                    "skipped_embeddings": int(embedding_report.get("skipped_existing") or 0),
                    "failed_chunks": embedding_report.get("failed_chunks") or [],
                    "errors": embedding_report.get("errors") or [],
                }
            )
        else:
            embedding_report = {
                "dry_run": True,
                "embedding_model": (embedding_provider_status().get("gemini_model") or embedding_provider_status().get("local_model")),
                "embedding_dimension": EMBEDDING_DIM,
                "chunks_to_embed": len(chunks),
                "embedded_chunks": 0,
                "skipped_existing": 0,
                "failed_chunks": [],
                "errors": [],
                "chunks_total": len(chunks),
                "chunks_inserted": 0,
                "chunks_skipped_duplicate": 0,
                "embedding_provider": embedding_provider_status(),
            }
    except Exception as exc:
        session.rollback()
        errors.append(str(exc))
        db_ingestion_report["errors"] = [*list(db_ingestion_report.get("errors") or []), str(exc)]
        if resolved_mode == "production":
            logger.exception("Solution book production ingestion failed")
    finally:
        if owns_db:
            session.close()

    ingestion_report = _ingestion_report(
        pages=pages,
        units=units,
        chunks=chunks,
        extraction_report=extraction_report,
        chunking_report=chunking_report,
        embedding_report=embedding_report,
        mode=resolved_mode,
        source_file_hash=source_file_hash,
    )
    if errors:
        ingestion_report["errors"] = errors
    report_path = out_dir / "ingestion_report.json"
    _write_json(report_path, ingestion_report)
    _write_json(out_dir / "embedding_report.json", embedding_report or {})
    _write_json(out_dir / "db_ingestion_report.json", db_ingestion_report)

    status = "completed"
    if errors:
        status = "failed" if resolved_mode == "production" else "dry_run_incomplete"
    elif blocked_pages:
        status = "dry_run_incomplete" if resolved_mode == "dry_run" else "failed"
    elif resolved_mode == "dry_run":
        status = "dry_run_completed"

    return SolutionBookIngestionResult(
        status=status,
        mode=resolved_mode,
        document_id=document_id,
        source_type=SOURCE_TYPE,
        source_id=source_id,
        pdf_path=str(pdf_path),
        output_dir=str(out_dir),
        source_file_hash=source_file_hash,
        pages_total=len(pages),
        pages_extracted_digitally=int(ingestion_report["pages_extracted_digitally"]),
        pages_needing_ocr=int(ingestion_report["pages_needing_ocr"]),
        pages_needing_vision=int(ingestion_report["pages_needing_vision"]),
        blocked_pages=blocked_pages,
        solution_units=len(units),
        chunks=len(chunks),
        chunks_inserted=int((embedding_report or {}).get("chunks_inserted") or 0),
        chunks_skipped_duplicate=int((embedding_report or {}).get("chunks_skipped_duplicate") or 0),
        duplicate_chunk_count=int(chunking_report.get("duplicate_chunk_count") or 0),
        warnings=warnings,
        errors=errors,
        reports={
            "audit_report": str(audit_report_path),
            "pages": str(out_dir / "pages.jsonl"),
            "solution_units": str(out_dir / "solution_units.jsonl"),
            "chunks": str(out_dir / "chunks.jsonl"),
            "extraction_report": str(out_dir / "extraction_report.json"),
            "ocr_review_report": str(out_dir / "ocr_review_report.json"),
            "chunking_report": str(out_dir / "chunking_report.json"),
            "embedding_report": str(out_dir / "embedding_report.json"),
            "db_ingestion_report": str(out_dir / "db_ingestion_report.json"),
            "ingestion_report": str(report_path),
        },
    )


def latest_solution_book_report(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    report_path = resolve_project_path(output_dir) / "ingestion_report.json"
    if not report_path.exists():
        raise FileNotFoundError(f"Solution book ingestion report not found: {report_path}")
    return json.loads(report_path.read_text(encoding="utf-8"))
