"""Reviewed RAG ingestion asset preparation for admin tooling.

This module only validates and prepares already-reviewed artifacts. It does
not run OCR/Vision, generate embeddings, or write vectors.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.chemistry import Lesson, Unit
from app.models.textbook import ContentSource, RagChunk
from app.rag.arabic_normalizer import normalize_arabic
from app.services.reviewed_curriculum_metadata import (
    DEFAULT_REQUIRED_CHUNK_METADATA,
    REVIEWED_METADATA_RELATIVE_PATH,
    ensure_reviewed_metadata_ready,
    evaluate_chunk_eligibility,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
REVIEWED_METADATA_VERSION_FALLBACK = "2026-06-reviewed-v1"
REPORT_DIR = REPO_ROOT / "reports/rag_ingestion_admin_tools"

TEXTBOOK_PDF = "src/data/textbooks/syria_grade_9/Chemistry.pdf"
SOLUTION_BOOK_PDF = "src/data/processed/Chemistry_Solution_Book.pdf"

BOOK_STRUCTURE = "data/processed/book_structure.json"
TEXTBOOK_PAGE_STRUCTURE = "data/processed/textbook/page_structure.jsonl"
TEXTBOOK_LESSON_MAP = "data/processed/textbook/textbook_lesson_map.reviewed.json"
TEXTBOOK_CHUNKS_PREVIEW = "data/processed/chunk_preview/textbook_chunks_preview.jsonl"
SOLUTION_PAGE_STRUCTURE = "data/processed/solution_book/solution_page_structure.jsonl"
SOLUTION_CHUNKS_CLEANED = "data/processed/solution_book/solution_chunks.cleaned.jsonl"
SOLUTION_CHUNKS_PREVIEW_CLEANED = "data/processed/chunk_preview/solution_book_chunks_preview.cleaned.jsonl"
SOLUTION_ALIGNMENT = "data/processed/solution_book/solution_textbook_alignment.json"
REVIEWED_METADATA = REVIEWED_METADATA_RELATIVE_PATH
SOLUTION_CHUNK_VALIDATION_REPORT = "reports/solution_chunk_cleanup/solution_chunk_validation_report.json"

TEXTBOOK_REVIEWED_CHUNKS_MIRROR = (
    "src/data/textbooks/syria_grade_9/reviewed_chunks/textbook_chunks_reviewed.jsonl"
)
TEXTBOOK_REVIEWED_METADATA_MIRROR = (
    "src/data/textbooks/syria_grade_9/reviewed_chunks/reviewed_curriculum_metadata.json"
)
SOLUTION_REVIEWED_CHUNKS_MIRROR = "src/data/processed/solution_book/solution_chunks.cleaned.reviewed.jsonl"
SOLUTION_REVIEWED_PREVIEW_MIRROR = (
    "src/data/processed/chunk_preview/solution_book_chunks_preview.cleaned.reviewed.jsonl"
)
SOLUTION_REVIEWED_METADATA_MIRROR = "src/data/processed/reviewed_curriculum_metadata.json"


@dataclass(frozen=True)
class CanonicalSourceSpec:
    source_type: str
    title: str
    file_path: str
    grade: str = "grade_9"
    subject: str = "chemistry"
    year: int = 2026


CANONICAL_SOURCES = [
    CanonicalSourceSpec(
        source_type="textbook",
        title="Chemistry Textbook - Grade 9 Syria",
        file_path=TEXTBOOK_PDF,
    ),
    CanonicalSourceSpec(
        source_type="solution_book",
        title="Chemistry Solution Book - Grade 9 Syria",
        file_path=SOLUTION_BOOK_PDF,
    ),
]


def _reviewed_artifact_paths_for_source(source_type: str) -> dict[str, str]:
    if source_type == "textbook":
        return {
            "reviewed_chunks_path": TEXTBOOK_REVIEWED_CHUNKS_MIRROR,
            "reviewed_preview_path": TEXTBOOK_REVIEWED_CHUNKS_MIRROR,
            "reviewed_metadata_path": TEXTBOOK_REVIEWED_METADATA_MIRROR,
        }
    if source_type == "solution_book":
        return {
            "reviewed_chunks_path": SOLUTION_REVIEWED_CHUNKS_MIRROR,
            "reviewed_preview_path": SOLUTION_REVIEWED_PREVIEW_MIRROR,
            "reviewed_metadata_path": SOLUTION_REVIEWED_METADATA_MIRROR,
        }
    return {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(relative_path: str | Path) -> Path:
    candidate = Path(relative_path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _read_json(relative_path: str | Path, default: Any = None) -> Any:
    path = _path(relative_path)
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(relative_path: str | Path, payload: Any) -> None:
    path = _path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(relative_path: str | Path) -> list[dict[str, Any]]:
    path = _path(relative_path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _write_jsonl(relative_path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = _path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def _copy_file(source_relative_path: str | Path, destination_relative_path: str | Path) -> str:
    source = _path(source_relative_path)
    destination = _path(destination_relative_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    return str(destination.relative_to(REPO_ROOT))


def _backup_file(relative_path: str | Path, suffix: str) -> str | None:
    path = _path(relative_path)
    if not path.exists():
        return None
    backup = path.with_name(f"{path.stem}.{suffix}{path.suffix}")
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    return str(backup.relative_to(REPO_ROOT))


def _sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pdf_page_count(path: Path) -> int | None:
    if not path.exists():
        return None
    with fitz.open(path) as doc:
        return int(doc.page_count)


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _file_modified_at(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _safe_read_jsonl(relative_path: str | Path) -> list[dict[str, Any]]:
    path = _path(relative_path)
    if not path.exists():
        return []
    return _read_jsonl(relative_path)


def _page_range_values(row: dict[str, Any], start_key: str, end_key: str | None = None) -> set[int]:
    start = row.get(start_key)
    end = row.get(end_key) if end_key else start
    if not isinstance(start, int):
        return set()
    if not isinstance(end, int):
        end = start
    if end < start:
        end = start
    return set(range(start, end + 1))


def _source_artifact_rows(source_type: str) -> dict[str, list[dict[str, Any]]]:
    if source_type == "textbook":
        return {
            "pages": _safe_read_jsonl(TEXTBOOK_PAGE_STRUCTURE),
            "chunks": _safe_read_jsonl(TEXTBOOK_REVIEWED_CHUNKS_MIRROR),
        }
    if source_type == "solution_book":
        return {
            "pages": _safe_read_jsonl(SOLUTION_PAGE_STRUCTURE),
            "chunks": _safe_read_jsonl(SOLUTION_REVIEWED_CHUNKS_MIRROR),
        }
    return {"pages": [], "chunks": []}


def _coverage_status(actual: int, expected: int | None, blockers: int = 0) -> str:
    if actual == 0:
        return "missing"
    if blockers > 0:
        return "partial"
    if expected is not None and expected > 0 and actual < expected:
        return "partial"
    return "complete"


def _reviewed_artifact_status(source_type: str, page_count: int | None) -> tuple[dict[str, int], str, str, list[str]]:
    rows = _source_artifact_rows(source_type)
    page_rows = rows["pages"]
    chunk_rows = rows["chunks"]

    if source_type == "textbook":
        extraction_pages: set[int] = {
            value
            for row in page_rows
            for value in _page_range_values(row, "printed_page_number")
        }
        chunk_pages: set[int] = {
            value
            for row in chunk_rows
            for value in _page_range_values(row, "printed_page_start", "printed_page_end")
        }
    else:
        extraction_pages = {
            value
            for row in page_rows
            for value in _page_range_values(row, "page_number")
        }
        chunk_pages = {
            value
            for row in chunk_rows
            for value in _page_range_values(row, "pdf_page_start", "pdf_page_end")
        }

    blocked_pages = sum(1 for row in page_rows if row.get("blocked") is True)
    needs_ocr_pages = sum(1 for row in page_rows if row.get("needs_ocr") is True)
    needs_vision_pages = sum(1 for row in page_rows if row.get("needs_vision") is True)
    chunk_quality = Counter(str(row.get("quality_status") or "unknown") for row in chunk_rows)
    missing_chunk_pages = sorted(extraction_pages - chunk_pages)
    warnings: list[str] = []
    if not page_rows:
        warnings.append("reviewed_page_structure_missing")
    if not chunk_rows:
        warnings.append("reviewed_chunks_missing")
    if missing_chunk_pages:
        warnings.append(f"missing_chunk_pages:{len(missing_chunk_pages)}")

    counts = {
        "extraction_pages": len(extraction_pages),
        "page_structure_rows": len(page_rows),
        "blocked_pages": blocked_pages,
        "needs_ocr_pages": needs_ocr_pages,
        "needs_vision_pages": needs_vision_pages,
        "reviewed_chunks": len(chunk_rows),
        "chunked_pages": len(chunk_pages),
        "missing_chunk_pages": len(missing_chunk_pages),
        "ready_chunks": int(chunk_quality.get("ready", 0)),
        "needs_review_chunks": int(chunk_quality.get("needs_review", 0)),
        "blocked_chunks": int(chunk_quality.get("blocked", 0)),
    }
    extraction_status = _coverage_status(len(extraction_pages), page_count, blockers=blocked_pages)
    chunk_status = _coverage_status(len(chunk_pages), len(extraction_pages) or page_count, blockers=counts["missing_chunk_pages"])
    return counts, extraction_status, chunk_status, warnings


def _embedding_status(chunk_count: int, embedded_chunk_count: int) -> str:
    if chunk_count <= 0 or embedded_chunk_count <= 0:
        return "not_embedded"
    if embedded_chunk_count < chunk_count:
        return "partial"
    return "embedded"


def _current_reviewed_metadata() -> dict[str, Any]:
    return _read_json(REVIEWED_METADATA, default={}) or {}


def _current_version() -> str:
    return str(_current_reviewed_metadata().get("version") or REVIEWED_METADATA_VERSION_FALLBACK)


def _base_embedding_contract() -> dict[str, Any]:
    return {
        "required": True,
        "source_of_truth": True,
        "required_chunk_metadata": DEFAULT_REQUIRED_CHUNK_METADATA,
        "allowed_source_types": ["textbook", "solution_book"],
        "blocked_quality_statuses": ["blocked"],
        "version_field": "reviewed_metadata_version",
        "lesson_id_optional_for_content_scopes": ["unit_level", "glossary", "project", "unit_questions"],
        "rag_search_quality_statuses": ["ready", "needs_review"],
        "student_generation_quality_statuses": ["ready"],
    }


def _validator_metadata_payload(version: str | None = None) -> dict[str, Any]:
    return {
        "version": version or _current_version(),
        "ready_for_embedding": True,
        "embedding_contract": _base_embedding_contract(),
    }


def _reviewed_metadata_status() -> dict[str, Any]:
    payload = _current_reviewed_metadata()
    return {
        "reviewed_metadata_version": payload.get("version"),
        "reviewed_metadata_status": payload.get("status") or "missing",
        "ready_for_embedding": bool(payload.get("ready_for_embedding") is True),
        "blocking_issues": list(payload.get("blocking_issues") or []),
        "missing_metadata_count": int(
            (payload.get("counts") or {}).get("textbook_chunk_preview_missing_required_metadata") or 0
        ),
        "manual_review_count": int((payload.get("counts") or {}).get("solution_chunks_needs_review") or 0),
    }


def canonical_source_statuses(db: Session | None = None) -> list[dict[str, Any]]:
    """Return current source file and optional database status for canonical PDFs."""

    reviewed = _reviewed_metadata_status()
    statuses: list[dict[str, Any]] = []
    for spec in CANONICAL_SOURCES:
        path = _path(spec.file_path)
        artifact_paths = _reviewed_artifact_paths_for_source(spec.source_type)
        source: ContentSource | None = None
        chunk_count = 0
        embedded_chunk_count = 0
        if db is not None:
            source = (
                db.query(ContentSource)
                .filter(ContentSource.file_path == spec.file_path)
                .order_by(ContentSource.created_at.desc())
                .first()
            )
            if source is not None:
                chunk_count = db.query(func.count(RagChunk.id)).filter(RagChunk.source_id == source.id).scalar() or 0
                embedded_chunk_count = (
                    db.query(func.count(RagChunk.id))
                    .filter(
                        RagChunk.source_id == source.id,
                        RagChunk.embedding.isnot(None),
                        RagChunk.embedding_status == "completed",
                    )
                    .scalar()
                    or 0
                )
        exists = path.exists()
        errors: list[str] = []
        page_count: int | None = None
        if exists:
            try:
                page_count = _pdf_page_count(path)
            except Exception as exc:  # pragma: no cover - corrupt PDF edge case
                errors.append(f"page_count_failed:{exc}")
        else:
            errors.append("file_missing")
        statuses.append(
            {
                **asdict(spec),
                "exists": exists,
                "file_size_bytes": path.stat().st_size if exists else None,
                "last_modified_at": _file_modified_at(path) if exists else None,
                "sha256": _sha256_file(path) if exists else None,
                "page_count": page_count,
                "source_id": source.id if source else None,
                "source_status": source.status if source else None,
                "chunk_count": int(chunk_count),
                "embedded_chunk_count": int(embedded_chunk_count),
                "reviewed_metadata_version": reviewed["reviewed_metadata_version"],
                "reviewed_metadata_status": reviewed["reviewed_metadata_status"],
                "ready_for_embedding": reviewed["ready_for_embedding"],
                "missing_metadata_count": reviewed["missing_metadata_count"],
                "manual_review_count": reviewed["manual_review_count"],
                "embedding_status": _embedding_status(int(chunk_count), int(embedded_chunk_count)),
                **artifact_paths,
                "errors": errors,
            }
        )
    return statuses


def _source_spec_for_id(source_id: str, db: Session | None = None) -> CanonicalSourceSpec | None:
    normalized = str(source_id).strip()
    for spec in CANONICAL_SOURCES:
        if normalized == spec.source_type:
            return spec
    if normalized.isdigit() and db is not None:
        source = db.get(ContentSource, int(normalized))
        if source is not None:
            for spec in CANONICAL_SOURCES:
                if source.file_path == spec.file_path or source.source_type == spec.source_type:
                    return spec
    return None


def rag_source_statuses(db: Session | None = None) -> list[dict[str, Any]]:
    """Return stable RAG source discovery statuses for the admin source view."""

    statuses: list[dict[str, Any]] = []
    for status in canonical_source_statuses(db):
        source_type = str(status["source_type"])
        artifact_counts, extraction_status, chunk_status, artifact_warnings = _reviewed_artifact_status(
            source_type,
            status.get("page_count"),
        )
        errors = list(status.get("errors") or [])
        warnings = artifact_warnings
        ingestion_status = "missing" if not status.get("exists") else status.get("source_status") or "not_registered"
        if artifact_counts["missing_chunk_pages"]:
            warnings.append(f"{source_type}_chunk_coverage_partial")
        counts = {
            "db_chunks": int(status.get("chunk_count") or 0),
            "db_embedded_chunks": int(status.get("embedded_chunk_count") or 0),
            "missing_metadata": int(status.get("missing_metadata_count") or 0),
            "manual_review": int(status.get("manual_review_count") or 0),
            **artifact_counts,
        }
        statuses.append(
            {
                "id": source_type,
                "db_source_id": status.get("source_id"),
                "source_type": source_type,
                "file_path": status["file_path"],
                "filename": Path(status["file_path"]).name,
                "checksum_sha256": status.get("sha256"),
                "page_count": status.get("page_count"),
                "file_size_bytes": status.get("file_size_bytes"),
                "last_modified_at": status.get("last_modified_at"),
                "ingestion_status": ingestion_status,
                "extraction_status": extraction_status,
                "chunk_status": chunk_status,
                "embedding_status": status.get("embedding_status") or "not_embedded",
                "errors": errors,
                "warnings": warnings,
                "counts": counts,
            }
        )
    return statuses


def rag_source_status(source_id: str, db: Session | None = None) -> dict[str, Any] | None:
    spec = _source_spec_for_id(source_id, db=db)
    if spec is None:
        return None
    for status in rag_source_statuses(db):
        if status["id"] == spec.source_type:
            return status
    return None


def scan_rag_source(source_id: str, db: Session) -> dict[str, Any] | None:
    """Register/update one canonical source and return its refreshed discovery status."""

    spec = _source_spec_for_id(source_id, db=db)
    if spec is None:
        return None
    validate_canonical_sources(db=db, register_missing=True)
    return rag_source_status(spec.source_type, db=db)


def validate_canonical_sources(db: Session | None = None, *, register_missing: bool = True) -> dict[str, Any]:
    """Validate and optionally register the two canonical PDF sources."""

    statuses = canonical_source_statuses(db)
    registered = 0
    updated = 0
    if db is not None:
        for status in statuses:
            spec = next(item for item in CANONICAL_SOURCES if item.file_path == status["file_path"])
            source = db.get(ContentSource, status["source_id"]) if status.get("source_id") else None
            metadata = {
                "canonical_source": True,
                "file_sha256": status["sha256"],
                "file_size_bytes": status["file_size_bytes"],
                "page_count": status["page_count"],
                "reviewed_metadata_version": status["reviewed_metadata_version"],
                "reviewed_metadata_status": status["reviewed_metadata_status"],
                "ready_for_embedding": status["ready_for_embedding"],
                "embedding_status": status["embedding_status"],
                "missing_metadata_count": status["missing_metadata_count"],
                "manual_review_count": status["manual_review_count"],
                "reviewed_chunks_path": status.get("reviewed_chunks_path"),
                "reviewed_preview_path": status.get("reviewed_preview_path"),
                "reviewed_metadata_path": status.get("reviewed_metadata_path"),
                "validated_at": _now_iso(),
            }
            if source is None and register_missing:
                source = ContentSource(
                    source_type=spec.source_type,
                    title=spec.title,
                    grade=spec.grade,
                    subject=spec.subject,
                    year=spec.year,
                    file_path=spec.file_path,
                    original_filename=Path(spec.file_path).name,
                    status="reviewed_source_ready" if status["exists"] else "missing",
                    metadata_json=metadata,
                )
                db.add(source)
                registered += 1
            elif source is not None:
                existing_metadata = source.metadata_json if isinstance(source.metadata_json, dict) else {}
                source.metadata_json = {**existing_metadata, **metadata}
                if source.status in {"pending", "missing", "reviewed_source_ready"}:
                    source.status = "reviewed_source_ready" if status["exists"] else "missing"
                updated += 1
        db.commit()
        statuses = canonical_source_statuses(db)

    missing = sum(1 for status in statuses if not status["exists"])
    reviewed = _reviewed_metadata_status()
    return {
        "sources": statuses,
        "registered_count": registered,
        "updated_count": updated,
        "missing_count": missing,
        "reviewed_metadata_version": reviewed["reviewed_metadata_version"],
        "ready_for_embedding": reviewed["ready_for_embedding"],
        "can_prepare_chunks": missing == 0,
    }


def _lesson_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    lesson_map = _read_json(TEXTBOOK_LESSON_MAP)
    lessons = list(lesson_map.get("lessons") or [])
    book_structure = _read_json(BOOK_STRUCTURE)
    units = list(book_structure.get("units") or [])
    lesson_by_id = {str(lesson["lesson_id"]): lesson for lesson in lessons if lesson.get("lesson_id")}
    unit_by_id = {str(unit["unit_id"]): unit for unit in units if unit.get("unit_id")}
    return lesson_by_id, unit_by_id, lessons


def _find_lesson_by_page(page: int | None, lessons: list[dict[str, Any]]) -> dict[str, Any] | None:
    if page is None:
        return None
    for lesson in lessons:
        start = lesson.get("printed_page_start")
        end = lesson.get("printed_page_end")
        if isinstance(start, int) and isinstance(end, int) and start <= page <= end:
            return lesson
    return None


def _find_unit_by_page(page: int | None, units: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if page is None:
        return None
    for unit in units.values():
        start = unit.get("printed_page_start")
        end = unit.get("printed_page_end")
        if isinstance(start, int) and isinstance(end, int) and start <= page <= end:
            return unit
    return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _content_scope_for_chunk(chunk: dict[str, Any], lesson: dict[str, Any] | None) -> str:
    if lesson is not None:
        return "lesson"
    chunk_type = str(chunk.get("chunk_type") or chunk.get("content_type") or "").strip()
    if chunk_type in {"glossary", "project", "unit_questions"}:
        return chunk_type
    return "unit_level"


def _quality_for_textbook_chunk(chunk: dict[str, Any], lesson: dict[str, Any] | None) -> str:
    if chunk.get("blocked") is True:
        return "blocked"
    if chunk.get("ends_cleanly") is False or chunk.get("bad_ending_reason"):
        return "needs_review"
    if lesson is not None:
        return str(lesson.get("quality_status") or "ready")
    score = float(chunk.get("quality_score") or 0)
    return "needs_review" if score and score < 0.75 else "ready"


def _metadata_issues_count(rows: list[dict[str, Any]], metadata_payload: dict[str, Any]) -> int:
    return sum(
        1
        for row in rows
        if not evaluate_chunk_eligibility(row, metadata_payload, legacy=False).embedding_allowed
    )


def prepare_textbook_chunks(*, write: bool = True, version: str | None = None) -> dict[str, Any]:
    rows = _read_jsonl(TEXTBOOK_CHUNKS_PREVIEW)
    metadata_payload = _validator_metadata_payload(version)
    missing_before = _metadata_issues_count(rows, metadata_payload)
    lesson_by_id, unit_by_id, lessons = _lesson_indexes()
    prepared: list[dict[str, Any]] = []
    quality_counts: Counter[str] = Counter()
    content_scope_counts: Counter[str] = Counter()
    changed = 0

    for raw in rows:
        chunk = dict(raw)
        page_start = _int_or_none(chunk.get("printed_page_start") or chunk.get("page_start") or chunk.get("page_number"))
        page_end = _int_or_none(chunk.get("printed_page_end") or chunk.get("page_end") or page_start)
        lesson = lesson_by_id.get(str(chunk.get("lesson_id") or "")) or _find_lesson_by_page(page_start, lessons)
        unit = unit_by_id.get(str(chunk.get("unit_id") or ""))
        if unit is None and lesson is not None:
            unit = unit_by_id.get(str(lesson.get("unit_id") or ""))
        if unit is None:
            unit = _find_unit_by_page(page_start, unit_by_id)
        content_scope = _content_scope_for_chunk(chunk, lesson)
        quality_status = _quality_for_textbook_chunk(chunk, lesson)
        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        content = str(chunk.get("content") or "")
        updates = {
            "source_type": "textbook",
            "unit_id": unit.get("unit_id") if unit else chunk.get("unit_id"),
            "lesson_id": lesson.get("lesson_id") if lesson else chunk.get("lesson_id"),
            "printed_page_start": page_start,
            "printed_page_end": page_end,
            "quality_status": quality_status,
            "reviewed_metadata_version": version or _current_version(),
            "content_scope": content_scope,
            "is_lesson_scoped": lesson is not None,
            "review_status": "reviewed",
            "metadata": {
                **metadata,
                "content_hash": metadata.get("content_hash") or _content_hash(content),
                "range_source": (lesson or unit or {}).get("range_source") or "reviewed_page_structure",
                "reviewed_metadata_version": version or _current_version(),
                "reviewed_curriculum_metadata_path": REVIEWED_METADATA_RELATIVE_PATH,
            },
        }
        before = json.dumps(chunk, ensure_ascii=False, sort_keys=True)
        chunk.update(updates)
        after = json.dumps(chunk, ensure_ascii=False, sort_keys=True)
        if before != after:
            changed += 1
        prepared.append(chunk)
        quality_counts[quality_status] += 1
        content_scope_counts[content_scope] += 1

    missing_after = _metadata_issues_count(prepared, metadata_payload)
    files_written: list[str] = []
    backup: str | None = None
    if write:
        backup = _backup_file(TEXTBOOK_CHUNKS_PREVIEW, "before_reviewed_metadata")
        _write_jsonl(TEXTBOOK_CHUNKS_PREVIEW, prepared)
        files_written.append(TEXTBOOK_CHUNKS_PREVIEW)
        files_written.append(_copy_file(TEXTBOOK_CHUNKS_PREVIEW, TEXTBOOK_REVIEWED_CHUNKS_MIRROR))

    return {
        "chunks_total": len(rows),
        "chunks_changed": changed,
        "missing_metadata_before": missing_before,
        "missing_metadata_after": missing_after,
        "quality_counts": dict(quality_counts),
        "content_scope_counts": dict(content_scope_counts),
        "backup_path": backup,
        "files_written": files_written,
    }


def prepare_solution_chunks(*, write: bool = True, version: str | None = None) -> dict[str, Any]:
    rows = _read_jsonl(SOLUTION_CHUNKS_CLEANED)
    preview_rows = _read_jsonl(SOLUTION_CHUNKS_PREVIEW_CLEANED)
    validation_report = _read_json(SOLUTION_CHUNK_VALIDATION_REPORT, default={}) or {}
    metadata_payload = _validator_metadata_payload(version)
    quality_counts: Counter[str] = Counter()
    missing_before = _metadata_issues_count(rows, metadata_payload)
    blocking_bad_endings = len(validation_report.get("bad_endings") or [])
    manual_review_from_report = len(validation_report.get("manual_review_bad_endings") or [])
    manual_review = 0
    prepared: list[dict[str, Any]] = []
    changed = 0
    for raw in rows:
        chunk = dict(raw)
        content = str(chunk.get("content") or chunk.get("content_ar") or "")
        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        updates = {
            "source_type": "solution_book",
            "reviewed_metadata_version": version or _current_version(),
            "quality_status": str(chunk.get("quality_status") or "needs_review"),
            "content_scope": "solution_unit",
            "metadata": {
                **metadata,
                "content_hash": metadata.get("content_hash") or _content_hash(content),
                "source_file": metadata.get("source_file") or SOLUTION_CHUNKS_CLEANED,
                "reviewed_metadata_version": version or _current_version(),
                "reviewed_curriculum_metadata_path": REVIEWED_METADATA_RELATIVE_PATH,
            },
        }
        before = json.dumps(chunk, ensure_ascii=False, sort_keys=True)
        chunk.update(updates)
        after = json.dumps(chunk, ensure_ascii=False, sort_keys=True)
        if before != after:
            changed += 1
        if chunk.get("quality_status") == "needs_review":
            manual_review += 1
        quality_counts[str(chunk.get("quality_status") or "unknown")] += 1
        prepared.append(chunk)
    missing_after = _metadata_issues_count(prepared, metadata_payload)
    files_written: list[str] = []
    backup: str | None = None
    if write and changed:
        backup = _backup_file(SOLUTION_CHUNKS_CLEANED, "before_reviewed_metadata")
        _write_jsonl(SOLUTION_CHUNKS_CLEANED, prepared)
        files_written.append(SOLUTION_CHUNKS_CLEANED)
    if write:
        files_written.append(_copy_file(SOLUTION_CHUNKS_CLEANED, SOLUTION_REVIEWED_CHUNKS_MIRROR))
        files_written.append(_copy_file(SOLUTION_CHUNKS_PREVIEW_CLEANED, SOLUTION_REVIEWED_PREVIEW_MIRROR))

    return {
        "chunks_total": len(rows),
        "preview_chunks_total": len(preview_rows),
        "chunks_changed": changed,
        "missing_metadata_before": missing_before,
        "missing_metadata_after": missing_after,
        "quality_counts": dict(quality_counts),
        "manual_review_count": max(manual_review, manual_review_from_report),
        "bad_endings_count": blocking_bad_endings,
        "backup_path": backup,
        "files_written": files_written,
        "legacy_chunks_used": False,
    }


def _reviewed_counts(
    textbook_result: dict[str, Any],
    solution_result: dict[str, Any],
) -> dict[str, Any]:
    lesson_map = _read_json(TEXTBOOK_LESSON_MAP)
    lessons = list(lesson_map.get("lessons") or [])
    book_structure = _read_json(BOOK_STRUCTURE)
    alignment = _read_json(SOLUTION_ALIGNMENT, default={}) or {}
    if isinstance(alignment, dict):
        alignment_records = alignment.get("items") or alignment.get("alignments") or []
    elif isinstance(alignment, list):
        alignment_records = alignment
    else:
        alignment_records = []
    solution_quality = solution_result.get("quality_counts") or {}
    textbook_quality = textbook_result.get("quality_counts") or {}
    return {
        "units": len(book_structure.get("units") or []),
        "textbook_lessons": len(lessons),
        "solution_alignment_records": len(alignment_records),
        "solution_chunks": int(solution_result.get("chunks_total") or 0),
        "ready_lessons": sum(1 for lesson in lessons if lesson.get("quality_status") == "ready"),
        "needs_review_lessons": sum(1 for lesson in lessons if lesson.get("quality_status") == "needs_review"),
        "blocked_lessons": sum(1 for lesson in lessons if lesson.get("quality_status") == "blocked"),
        "textbook_chunk_preview_chunks": int(textbook_result.get("chunks_total") or 0),
        "textbook_chunk_preview_missing_required_metadata": int(textbook_result.get("missing_metadata_after") or 0),
        "textbook_chunks_ready": int(textbook_quality.get("ready") or 0),
        "textbook_chunks_needs_review": int(textbook_quality.get("needs_review") or 0),
        "textbook_chunks_blocked": int(textbook_quality.get("blocked") or 0),
        "solution_chunks_ready": int(solution_quality.get("ready") or 0),
        "solution_chunks_needs_review": int(solution_quality.get("needs_review") or 0),
        "solution_chunks_blocked": int(solution_quality.get("blocked") or 0),
        "solution_chunk_bad_endings": int(solution_result.get("bad_endings_count") or 0),
        "manual_review_chunks": int(solution_result.get("manual_review_count") or 0),
    }


def _build_reviewed_metadata(
    textbook_result: dict[str, Any],
    solution_result: dict[str, Any],
    *,
    version: str,
) -> dict[str, Any]:
    counts = _reviewed_counts(textbook_result, solution_result)
    blocking_issues: list[str] = []
    if counts["textbook_chunk_preview_missing_required_metadata"]:
        blocking_issues.append(
            f"textbook_chunk_preview_missing_required_metadata:{counts['textbook_chunk_preview_missing_required_metadata']}"
        )
    if counts["solution_chunk_bad_endings"]:
        blocking_issues.append(f"solution_chunk_bad_endings:{counts['solution_chunk_bad_endings']}")
    if counts["textbook_chunks_blocked"] or counts["solution_chunks_blocked"]:
        blocking_issues.append(
            f"blocked_chunks:{counts['textbook_chunks_blocked'] + counts['solution_chunks_blocked']}"
        )

    ready = not blocking_issues
    source_statuses = canonical_source_statuses(None)
    return {
        "version": version,
        "status": "reviewed" if ready else "blocked",
        "created_at": _current_reviewed_metadata().get("created_at") or _now_iso(),
        "reviewed_at": _now_iso(),
        "ready_for_embedding": ready,
        "paths": {
            "textbook_pdf": TEXTBOOK_PDF,
            "solution_book_pdf": SOLUTION_BOOK_PDF,
            "book_structure": BOOK_STRUCTURE,
            "textbook_page_structure": TEXTBOOK_PAGE_STRUCTURE,
            "textbook_lesson_map": TEXTBOOK_LESSON_MAP,
            "textbook_chunk_preview": TEXTBOOK_CHUNKS_PREVIEW,
            "solution_chunks": SOLUTION_CHUNKS_CLEANED,
            "solution_chunk_preview": SOLUTION_CHUNKS_PREVIEW_CLEANED,
            "solution_alignment": SOLUTION_ALIGNMENT,
        },
        "sources": source_statuses,
        "quality": {
            "textbook_pages_blocked": [],
            "textbook_pages_needing_ocr": [],
            "textbook_pages_needing_vision": [],
            "solution_chunks_bad_endings": counts["solution_chunk_bad_endings"],
            "manual_review_chunks": counts["manual_review_chunks"],
            "manual_review_chunks_block_embedding": False,
            "student_generation_uses_ready_only": True,
        },
        "counts": counts,
        "blocking_issues": blocking_issues,
        "embedding_contract": _base_embedding_contract(),
    }


def write_reviewed_metadata(
    textbook_result: dict[str, Any],
    solution_result: dict[str, Any],
    *,
    write: bool = True,
    version: str | None = None,
) -> dict[str, Any]:
    payload = _build_reviewed_metadata(
        textbook_result,
        solution_result,
        version=version or _current_version(),
    )
    backup = None
    if write:
        backup = _backup_file(REVIEWED_METADATA, "before_rag_admin_prepare")
        _write_json(REVIEWED_METADATA, payload)
        _copy_file(REVIEWED_METADATA, TEXTBOOK_REVIEWED_METADATA_MIRROR)
        _copy_file(REVIEWED_METADATA, SOLUTION_REVIEWED_METADATA_MIRROR)
    return {
        "payload": payload,
        "backup_path": backup,
        "files_written": [
            REVIEWED_METADATA,
            TEXTBOOK_REVIEWED_METADATA_MIRROR,
            SOLUTION_REVIEWED_METADATA_MIRROR,
        ]
        if write
        else [],
    }


def embedding_readiness() -> dict[str, Any]:
    payload = _current_reviewed_metadata()
    counts = payload.get("counts") or {}
    contract = payload.get("embedding_contract") or _base_embedding_contract()
    return {
        "reviewed_metadata_version": payload.get("version"),
        "status": payload.get("status") or "missing",
        "ready_for_embedding": bool(payload.get("ready_for_embedding") is True),
        "blocking_issues": list(payload.get("blocking_issues") or []),
        "required_chunk_metadata": list(contract.get("required_chunk_metadata") or DEFAULT_REQUIRED_CHUNK_METADATA),
        "allowed_source_types": list(contract.get("allowed_source_types") or ["textbook", "solution_book"]),
        "embedding_model": "gemini-embedding-001",
        "embedding_dimension": 768,
        "vector_store": "rag_chunks",
        "vector_index": "ivfflat/vector_cosine_ops",
        "textbook_chunks_total": int(counts.get("textbook_chunk_preview_chunks") or 0),
        "textbook_missing_metadata_count": int(
            counts.get("textbook_chunk_preview_missing_required_metadata") or 0
        ),
        "solution_chunks_total": int(counts.get("solution_chunks") or 0),
        "solution_manual_review_count": int(counts.get("manual_review_chunks") or counts.get("solution_chunks_needs_review") or 0),
        "solution_bad_endings_count": int(counts.get("solution_chunk_bad_endings") or 0),
        "ready_chunk_count": int(counts.get("textbook_chunks_ready") or 0) + int(counts.get("solution_chunks_ready") or 0),
        "needs_review_chunk_count": int(counts.get("textbook_chunks_needs_review") or 0)
        + int(counts.get("solution_chunks_needs_review") or 0),
        "blocked_chunk_count": int(counts.get("textbook_chunks_blocked") or 0)
        + int(counts.get("solution_chunks_blocked") or 0),
    }


def prepare_reviewed_chunks(
    *,
    write: bool = True,
    include_textbook: bool = True,
    include_solution_book: bool = True,
) -> dict[str, Any]:
    """Prepare reviewed chunks and update embedding readiness metadata."""

    version = _current_version()
    current_metadata = _current_reviewed_metadata()
    current_counts = current_metadata.get("counts") or {}
    textbook_result = {
        "chunks_total": int(current_counts.get("textbook_chunk_preview_chunks") or 0),
        "missing_metadata_after": int(current_counts.get("textbook_chunk_preview_missing_required_metadata") or 0),
        "quality_counts": {},
        "files_written": [],
    }
    solution_result = {
        "chunks_total": int(current_counts.get("solution_chunks") or 0),
        "missing_metadata_after": 0,
        "quality_counts": {},
        "manual_review_count": int(current_counts.get("solution_chunks_needs_review") or 0),
        "bad_endings_count": int(current_counts.get("solution_chunk_bad_endings") or 0),
        "files_written": [],
    }
    if include_textbook:
        textbook_result = prepare_textbook_chunks(write=write, version=version)
    if include_solution_book:
        solution_result = prepare_solution_chunks(write=write, version=version)
    metadata_result = write_reviewed_metadata(
        textbook_result,
        solution_result,
        write=write,
        version=version,
    )
    result = {
        "status": "passed" if metadata_result["payload"].get("ready_for_embedding") else "blocked",
        "write": write,
        "reviewed_metadata_version": version,
        "ready_for_embedding": bool(metadata_result["payload"].get("ready_for_embedding") is True),
        "textbook": textbook_result,
        "solution_book": solution_result,
        "counts": metadata_result["payload"].get("counts") or {},
        "blocking_issues": list(metadata_result["payload"].get("blocking_issues") or []),
        "files_written": [
            *textbook_result.get("files_written", []),
            *solution_result.get("files_written", []),
            *metadata_result.get("files_written", []),
        ],
        "backups": [
            item
            for item in [
                textbook_result.get("backup_path"),
                solution_result.get("backup_path"),
                metadata_result.get("backup_path"),
            ]
            if item
        ],
    }
    if write:
        write_prepare_report(result)
    return result


def _selected_source_types(*, include_textbook: bool, include_solution_book: bool) -> list[str]:
    selected: list[str] = []
    if include_textbook:
        selected.append("textbook")
    if include_solution_book:
        selected.append("solution_book")
    return selected


def _reviewed_chunk_rows_for_source(source_type: str) -> list[dict[str, Any]]:
    if source_type == "textbook":
        return _read_jsonl(TEXTBOOK_REVIEWED_CHUNKS_MIRROR)
    if source_type == "solution_book":
        return _read_jsonl(SOLUTION_REVIEWED_CHUNKS_MIRROR)
    raise ValueError(f"Unsupported source_type: {source_type}")


def _source_for_type(db: Session, source_type: str) -> ContentSource:
    spec = next((item for item in CANONICAL_SOURCES if item.source_type == source_type), None)
    if spec is None:
        raise ValueError(f"Unsupported source_type: {source_type}")
    source = (
        db.query(ContentSource)
        .filter(ContentSource.source_type == spec.source_type, ContentSource.file_path == spec.file_path)
        .order_by(ContentSource.created_at.desc())
        .first()
    )
    if source is None:
        raise RuntimeError(f"Canonical source was not registered for {source_type}")
    return source


def _curriculum_fk_maps(db: Session) -> tuple[dict[str, int], dict[str, int]]:
    unit_map: dict[str, int] = {}
    for unit in db.query(Unit).all():
        unit_map[f"unit_{int(unit.unit_number):02d}"] = int(unit.id)

    lesson_map: dict[str, int] = {}
    lessons = db.query(Lesson).all()
    for lesson in lessons:
        unit = lesson.chapter.unit if lesson.chapter and lesson.chapter.unit else None
        if unit is not None:
            lesson_map[f"unit_{int(unit.unit_number):02d}_lesson_{int(lesson.order):02d}"] = int(lesson.id)
        if lesson.title_ar:
            lesson_map.setdefault(f"title:{normalize_arabic(lesson.title_ar)}", int(lesson.id))
    return unit_map, lesson_map


def _db_lesson_id_for_chunk(chunk: dict[str, Any], lesson_map: dict[str, int]) -> int | None:
    stable = str(chunk.get("lesson_id") or chunk.get("linked_textbook_lesson_id") or "")
    if stable and stable in lesson_map:
        return lesson_map[stable]
    title = str(chunk.get("lesson_title") or chunk.get("linked_lesson_title") or "")
    if title:
        return lesson_map.get(f"title:{normalize_arabic(title)}")
    return None


def _chunk_page_number(chunk: dict[str, Any], source_type: str) -> int | None:
    if source_type == "solution_book":
        return _int_or_none(chunk.get("printed_page_start") or chunk.get("pdf_page_start"))
    return _int_or_none(chunk.get("printed_page_start") or chunk.get("page_start") or chunk.get("page_number"))


def _chunk_metadata_for_db(chunk: dict[str, Any], source_type: str) -> dict[str, Any]:
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    content = str(chunk.get("content") or chunk.get("content_ar") or "")
    reviewed_fields = {
        "reviewed_chunk_id": chunk.get("reviewed_chunk_id") or chunk.get("chunk_id"),
        "chunk_type": chunk.get("chunk_type") or chunk.get("content_type"),
        "source_type": source_type,
        "unit_id": chunk.get("unit_id"),
        "lesson_id": chunk.get("lesson_id") or chunk.get("linked_textbook_lesson_id"),
        "lesson_title": chunk.get("lesson_title") or chunk.get("linked_lesson_title"),
        "subtopic_title": chunk.get("subtopic_title"),
        "printed_page_start": chunk.get("printed_page_start") or chunk.get("page_start"),
        "printed_page_end": chunk.get("printed_page_end") or chunk.get("page_end") or chunk.get("printed_page_start"),
        "pdf_page_start": chunk.get("pdf_page_start"),
        "pdf_page_end": chunk.get("pdf_page_end"),
        "quality_status": chunk.get("quality_status"),
        "review_status": chunk.get("review_status"),
        "reviewed_metadata_version": chunk.get("reviewed_metadata_version") or _current_version(),
        "content_scope": chunk.get("content_scope"),
        "ends_cleanly": chunk.get("ends_cleanly"),
        "bad_ending_reason": chunk.get("bad_ending_reason"),
        "solution_unit_id": chunk.get("solution_unit_id"),
        "linked_textbook_lesson_id": chunk.get("linked_textbook_lesson_id"),
        "linked_lesson_title": chunk.get("linked_lesson_title"),
        "exercise_number": chunk.get("exercise_number"),
        "question_number": chunk.get("question_number"),
        "token_estimate": chunk.get("token_estimate"),
    }
    return {
        **metadata,
        **{key: value for key, value in reviewed_fields.items() if value not in (None, "", [])},
        "content_hash": metadata.get("content_hash") or _content_hash(content),
        "reviewed_curriculum_metadata_path": REVIEWED_METADATA_RELATIVE_PATH,
    }


def _load_reviewed_chunks_to_rag_clear_legacy(
    db: Session,
    *,
    clear_existing: bool = True,
    include_textbook: bool = True,
    include_solution_book: bool = True,
) -> dict[str, Any]:
    """Load already-reviewed chunk files into ``rag_chunks`` without embedding.

    This is the missing bridge between reviewed JSONL assets and the DB-backed
    re-embedding pipeline. It intentionally does not call Gemini or write
    vectors; rows are inserted with ``embedding_status='pending'`` and should be
    embedded by ``scripts/reembed_rag.py`` or the admin re-embed job.
    """

    reviewed_metadata = ensure_reviewed_metadata_ready()
    selected = _selected_source_types(include_textbook=include_textbook, include_solution_book=include_solution_book)
    if not selected:
        raise ValueError("At least one source type must be selected.")

    validate_canonical_sources(db=db, register_missing=True)
    unit_map, lesson_map = _curriculum_fk_maps(db)

    source_results: dict[str, Any] = {}
    inserted_total = 0
    deleted_total = 0
    skipped_blocked_total = 0
    skipped_missing_total = 0
    skipped_empty_total = 0

    for source_type in selected:
        source = _source_for_type(db, source_type)
        rows = _reviewed_chunk_rows_for_source(source_type)
        deleted = 0
        if clear_existing:
            deleted = (
                db.query(RagChunk)
                .filter(RagChunk.source_id == source.id)
                .delete(synchronize_session=False)
            )

        inserted = 0
        skipped_blocked = 0
        skipped_missing = 0
        skipped_empty = 0
        quality_counts: Counter[str] = Counter()
        content_type_counts: Counter[str] = Counter()
        for row in rows:
            content = str(row.get("content") or row.get("content_ar") or "").strip()
            if not content:
                skipped_empty += 1
                continue
            candidate = {**row, "source_type": row.get("source_type") or source_type}
            decision = evaluate_chunk_eligibility(candidate, reviewed_metadata, legacy=False)
            if not decision.embedding_allowed:
                if "blocked_quality_status" in decision.reason_codes:
                    skipped_blocked += 1
                else:
                    skipped_missing += 1
                continue

            metadata = {
                **_chunk_metadata_for_db(row, source_type),
                **decision.normalized_metadata,
            }
            stable_unit_id = str(row.get("unit_id") or "")
            db_unit_id = unit_map.get(stable_unit_id)
            db_lesson_id = _db_lesson_id_for_chunk(row, lesson_map)
            content_type = str(row.get("chunk_type") or row.get("content_type") or "text")[:40]
            page_number = _chunk_page_number(row, source_type)
            db.add(
                RagChunk(
                    source_id=source.id,
                    unit_id=db_unit_id,
                    chapter_id=None,
                    lesson_id=db_lesson_id,
                    topic_id=None,
                    page_number=page_number,
                    chunk_index=inserted,
                    content=content,
                    normalized_content=normalize_arabic(content),
                    content_type=content_type,
                    source_type=source_type,
                    extraction_method="reviewed_jsonl",
                    language="ar",
                    embedding=None,
                    embedding_model=None,
                    embedding_status="pending",
                    embedding_error=None,
                    metadata_json=metadata,
                )
            )
            inserted += 1
            quality_counts[str(metadata.get("quality_status") or "unknown")] += 1
            content_type_counts[content_type] += 1

        source_metadata = source.metadata_json if isinstance(source.metadata_json, dict) else {}
        source.metadata_json = {
            **source_metadata,
            "last_reviewed_chunk_load": {
                "at": _now_iso(),
                "clear_existing": clear_existing,
                "rows_seen": len(rows),
                "chunks_deleted": int(deleted),
                "chunks_inserted": inserted,
                "skipped_blocked": skipped_blocked,
                "skipped_missing_metadata": skipped_missing,
                "skipped_empty_content": skipped_empty,
                "quality_counts": dict(quality_counts),
                "content_type_counts": dict(content_type_counts),
                "reviewed_metadata_version": reviewed_metadata.get("version"),
            },
        }
        source.status = "reviewed_chunks_loaded"
        source_results[source_type] = {
            "source_id": source.id,
            "rows_seen": len(rows),
            "chunks_deleted": int(deleted),
            "chunks_inserted": inserted,
            "skipped_blocked": skipped_blocked,
            "skipped_missing_metadata": skipped_missing,
            "skipped_empty_content": skipped_empty,
            "quality_counts": dict(quality_counts),
            "content_type_counts": dict(content_type_counts),
        }
        inserted_total += inserted
        deleted_total += int(deleted)
        skipped_blocked_total += skipped_blocked
        skipped_missing_total += skipped_missing
        skipped_empty_total += skipped_empty

    db.commit()
    return {
        "status": "loaded",
        "clear_existing": clear_existing,
        "reviewed_metadata_version": reviewed_metadata.get("version"),
        "sources": source_results,
        "chunks_deleted": deleted_total,
        "chunks_inserted": inserted_total,
        "skipped_blocked": skipped_blocked_total,
        "skipped_missing_metadata": skipped_missing_total,
        "skipped_empty_content": skipped_empty_total,
        "embedding_status": "pending",
        "next_step": "Run scripts/reembed_rag.py to generate pgvector embeddings.",
    }


def load_reviewed_chunks_to_rag(
    db: Session,
    *,
    clear_existing: bool = False,
    dry_run: bool = False,
    include_textbook: bool = True,
    include_solution_book: bool = True,
) -> dict[str, Any]:
    """Idempotently load reviewed chunks without generating or writing vectors."""

    reviewed_metadata = ensure_reviewed_metadata_ready()
    selected = _selected_source_types(
        include_textbook=include_textbook,
        include_solution_book=include_solution_book,
    )
    if not selected:
        raise ValueError("At least one source type must be selected.")
    if clear_existing and db.get_bind().dialect.name != "sqlite":
        raise ValueError("CLEAR_EXISTING_DISABLED_IN_PRODUCTION")

    validate_canonical_sources(db=db, register_missing=not dry_run)
    unit_map, lesson_map = _curriculum_fk_maps(db)
    source_results: dict[str, Any] = {}
    totals: Counter[str] = Counter()
    pending_inserts: list[RagChunk] = []
    pending_updates: list[tuple[RagChunk, dict[str, Any]]] = []
    pending_stale: list[RagChunk] = []
    pending_deletes: list[RagChunk] = []
    pending_source_updates: list[tuple[ContentSource, dict[str, Any]]] = []

    def content_hash_for(value: str) -> str:
        return _content_hash(value.strip())

    def identity_for_row(row: dict[str, Any], source_type: str) -> tuple[str, str]:
        content = str(row.get("content") or row.get("content_ar") or "").strip()
        nested = row.get("metadata") if isinstance(row.get("metadata"), dict) else row.get("metadata_json")
        nested = nested if isinstance(nested, dict) else {}
        reviewed_id = row.get("reviewed_chunk_id") or row.get("chunk_id") or nested.get("reviewed_chunk_id")
        content_hash = str(nested.get("content_hash") or row.get("content_hash") or content_hash_for(content))
        if reviewed_id not in (None, "", []):
            return f"{source_type}:id:{reviewed_id}", content_hash
        return f"{source_type}:hash:{content_hash}", content_hash

    def identity_for_db(chunk: RagChunk) -> tuple[str, str]:
        metadata = chunk.metadata_json if isinstance(chunk.metadata_json, dict) else {}
        reviewed_id = metadata.get("reviewed_chunk_id") or metadata.get("chunk_id")
        content_hash = str(metadata.get("content_hash") or content_hash_for(chunk.content or ""))
        if reviewed_id not in (None, "", []):
            return f"{chunk.source_type}:id:{reviewed_id}", content_hash
        return f"{chunk.source_type}:hash:{content_hash}", content_hash

    try:
        for source_type in selected:
            try:
                source = _source_for_type(db, source_type)
            except RuntimeError:
                if not dry_run:
                    raise
                # A dry-run must work before an admin has registered the
                # canonical source. Use an in-memory source descriptor and
                # never attach it to the session.
                spec = next(item for item in CANONICAL_SOURCES if item.source_type == source_type)
                source = ContentSource(
                    source_type=spec.source_type,
                    title=spec.title,
                    grade=spec.grade,
                    subject=spec.subject,
                    year=spec.year,
                    file_path=spec.file_path,
                    original_filename=Path(spec.file_path).name,
                    status="reviewed_source_ready",
                )
            rows = _reviewed_chunk_rows_for_source(source_type)
            existing_rows = list(
                db.query(RagChunk)
                .filter(RagChunk.source_id == source.id)
                .order_by(RagChunk.chunk_index.asc(), RagChunk.id.asc())
                .all()
            )
            existing_by_identity: dict[str, RagChunk] = {}
            for existing in existing_rows:
                identity, _hash = identity_for_db(existing)
                existing_by_identity.setdefault(identity, existing)

            if clear_existing:
                pending_deletes.extend(existing_rows)
                existing_by_identity = {}
                totals["deleted"] += len(existing_rows)

            seen_identities: set[str] = set()
            source_inserts: list[RagChunk] = []
            inserted = updated = unchanged = stale = 0
            skipped_blocked = skipped_missing = skipped_empty = embedding_reset = 0
            quality_counts: Counter[str] = Counter()
            content_type_counts: Counter[str] = Counter()

            for row_index, row in enumerate(rows):
                content = str(row.get("content") or row.get("content_ar") or "").strip()
                if not content:
                    skipped_empty += 1
                    continue
                candidate = {
                    **row,
                    "content": content,
                    "source_type": row.get("source_type") or source_type,
                }
                decision = evaluate_chunk_eligibility(candidate, reviewed_metadata, legacy=False)
                identity, content_hash = identity_for_row(row, source_type)
                seen_identities.add(identity)
                existing = existing_by_identity.get(identity)

                if not decision.embedding_allowed:
                    if "blocked_quality_status" in decision.reason_codes:
                        skipped_blocked += 1
                    else:
                        skipped_missing += 1
                    if existing and "blocked_quality_status" in decision.reason_codes:
                        metadata = {
                            **(existing.metadata_json if isinstance(existing.metadata_json, dict) else {}),
                            **decision.normalized_metadata,
                            "content_hash": content_hash,
                            "stale": False,
                        }
                        pending_updates.append(
                            (
                                existing,
                                {
                                    "metadata_json": metadata,
                                    "embedding": None,
                                    "embedding_model": None,
                                    "embedding_updated_at": None,
                                    "embedding_status": "skipped",
                                    "embedding_error": "blocked_quality_status",
                                },
                            )
                        )
                        updated += 1
                    continue

                metadata = {
                    **_chunk_metadata_for_db(row, source_type),
                    **decision.normalized_metadata,
                    "reviewed_chunk_id": row.get("reviewed_chunk_id") or row.get("chunk_id"),
                    "content_hash": content_hash,
                    "reviewed_metadata_version": reviewed_metadata.get("version"),
                    "stale": False,
                }
                metadata = {key: value for key, value in metadata.items() if value not in (None, "", [])}
                db_unit_id = unit_map.get(str(row.get("unit_id") or ""))
                db_lesson_id = _db_lesson_id_for_chunk(row, lesson_map)
                content_type = str(row.get("chunk_type") or row.get("content_type") or "text")[:40]
                page_number = _chunk_page_number(row, source_type)

                if existing is None:
                    source_inserts.append(
                        RagChunk(
                            source_id=source.id,
                            unit_id=db_unit_id,
                            chapter_id=None,
                            lesson_id=db_lesson_id,
                            page_number=page_number,
                            chunk_index=row_index,
                            content=content,
                            normalized_content=normalize_arabic(content),
                            content_type=content_type,
                            source_type=source_type,
                            extraction_method="reviewed_jsonl",
                            language="ar",
                            embedding=None,
                            embedding_model=None,
                            embedding_status="pending",
                            embedding_error=None,
                            metadata_json=metadata,
                        )
                    )
                    inserted += 1
                else:
                    old_metadata = existing.metadata_json if isinstance(existing.metadata_json, dict) else {}
                    old_hash = str(old_metadata.get("content_hash") or content_hash_for(existing.content or ""))
                    content_same = old_hash == content_hash and (existing.content or "").strip() == content
                    update = {
                        "unit_id": db_unit_id,
                        "lesson_id": db_lesson_id,
                        "page_number": page_number,
                        "chunk_index": row_index,
                        "content": content,
                        "normalized_content": normalize_arabic(content),
                        "content_type": content_type,
                        "source_type": source_type,
                        "extraction_method": "reviewed_jsonl",
                        "metadata_json": metadata,
                    }
                    if content_same:
                        if existing.embedding_status == "skipped" and old_metadata.get("stale"):
                            update.update({"embedding_status": "pending", "embedding_error": None})
                            embedding_reset += 1
                        pending_updates.append((existing, update))
                        if old_metadata == metadata and "embedding_status" not in update:
                            unchanged += 1
                        else:
                            updated += 1
                    else:
                        update.update(
                            {
                                "embedding": None,
                                "embedding_model": None,
                                "embedding_status": "pending",
                                "embedding_error": None,
                            }
                        )
                        pending_updates.append((existing, update))
                        updated += 1
                        embedding_reset += 1

                quality_counts[str(metadata.get("quality_status") or "unknown")] += 1
                content_type_counts[content_type] += 1

            pending_inserts.extend(source_inserts)
            if not clear_existing:
                for existing in existing_rows:
                    identity, _hash = identity_for_db(existing)
                    if (
                        identity not in seen_identities
                        and existing.extraction_method == "reviewed_jsonl"
                        and not (existing.metadata_json or {}).get("stale")
                    ):
                        pending_stale.append(existing)
                        stale += 1

            source_metadata = source.metadata_json if isinstance(source.metadata_json, dict) else {}
            pending_source_updates.append(
                (
                    source,
                    {
                        **source_metadata,
                        "last_reviewed_chunk_load": {
                            "at": _now_iso(),
                            "dry_run": dry_run,
                            "clear_existing": clear_existing,
                            "rows_seen": len(rows),
                            "chunks_deleted": len(existing_rows) if clear_existing else 0,
                            "chunks_inserted": inserted,
                            "chunks_updated": updated,
                            "chunks_unchanged": unchanged,
                            "chunks_stale": stale,
                            "skipped_blocked": skipped_blocked,
                            "skipped_missing_metadata": skipped_missing,
                            "skipped_empty_content": skipped_empty,
                            "embedding_reset": embedding_reset,
                            "quality_counts": dict(quality_counts),
                            "content_type_counts": dict(content_type_counts),
                            "reviewed_metadata_version": reviewed_metadata.get("version"),
                        },
                    },
                )
            )
            source_results[source_type] = {
                "source_id": source.id,
                "rows_seen": len(rows),
                "chunks_deleted": len(existing_rows) if clear_existing else 0,
                "chunks_inserted": inserted,
                "chunks_updated": updated,
                "chunks_unchanged": unchanged,
                "chunks_stale": stale,
                "skipped_blocked": skipped_blocked,
                "skipped_missing_metadata": skipped_missing,
                "skipped_empty_content": skipped_empty,
                "embedding_reset": embedding_reset,
                "quality_counts": dict(quality_counts),
                "content_type_counts": dict(content_type_counts),
            }
            totals.update(
                {
                    "inserted": inserted,
                    "updated": updated,
                    "unchanged": unchanged,
                    "stale": stale,
                    "skipped_blocked": skipped_blocked,
                    "skipped_missing": skipped_missing,
                    "skipped_empty": skipped_empty,
                    "embedding_reset": embedding_reset,
                }
            )

        if not dry_run:
            for row in pending_deletes:
                db.delete(row)
            for row in pending_inserts:
                db.add(row)
            for row, updates in pending_updates:
                for key, value in updates.items():
                    setattr(row, key, value)
            for row in pending_stale:
                metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
                row.metadata_json = {**metadata, "stale": True, "stale_reason": "stale_reviewed_chunk"}
                row.embedding_status = "skipped"
                row.embedding_error = "stale_reviewed_chunk"
            for source, metadata in pending_source_updates:
                source.metadata_json = metadata
                source.status = "reviewed_chunks_loaded"
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise

    return {
        "status": "dry_run" if dry_run else "loaded",
        "clear_existing": clear_existing,
        "dry_run": dry_run,
        "would_write": bool(
            totals["inserted"]
            or totals["updated"]
            or totals["stale"]
            or totals["deleted"]
        ),
        "reviewed_metadata_version": reviewed_metadata.get("version"),
        "sources": source_results,
        "chunks_deleted": totals["deleted"],
        "chunks_inserted": totals["inserted"],
        "chunks_updated": totals["updated"],
        "chunks_unchanged": totals["unchanged"],
        "chunks_stale": totals["stale"],
        "embedding_reset": totals["embedding_reset"],
        "skipped_blocked": totals["skipped_blocked"],
        "skipped_missing_metadata": totals["skipped_missing"],
        "skipped_empty_content": totals["skipped_empty"],
        "embedding_status": "pending",
        "next_step": "Run scripts/reembed_rag.py to generate pgvector embeddings.",
    }


def write_prepare_report(result: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "prepare_reviewed_chunks_report.json"
    md_path = REPORT_DIR / "prepare_reviewed_chunks_report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# RAG Reviewed Chunk Preparation",
        "",
        f"- Status: `{result['status']}`",
        f"- Reviewed metadata version: `{result['reviewed_metadata_version']}`",
        f"- Ready for embedding: `{result['ready_for_embedding']}`",
        f"- Textbook chunks: `{result['textbook'].get('chunks_total', 0)}`",
        f"- Textbook missing metadata after: `{result['textbook'].get('missing_metadata_after', 0)}`",
        f"- Solution chunks: `{result['solution_book'].get('chunks_total', 0)}`",
        f"- Solution bad endings: `{result['solution_book'].get('bad_endings_count', 0)}`",
        f"- Solution manual-review chunks: `{result['solution_book'].get('manual_review_count', 0)}`",
        "",
        "## Files Written",
        "",
        *[f"- `{path}`" for path in result.get("files_written", [])],
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
