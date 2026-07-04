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

from app.models.textbook import ContentSource, RagChunk
from app.services.reviewed_curriculum_metadata import (
    DEFAULT_REQUIRED_CHUNK_METADATA,
    REVIEWED_METADATA_RELATIVE_PATH,
    chunk_is_embedding_ready,
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
                "embedding_status": "embedded" if embedded_chunk_count else "not_embedded",
                **artifact_paths,
                "errors": errors,
            }
        )
    return statuses


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
    return sum(1 for row in rows if chunk_is_embedding_ready(row, metadata_payload)[0] is False)


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
