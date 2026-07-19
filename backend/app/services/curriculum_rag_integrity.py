"""Read-only curriculum-to-RAG integrity audit and report generation."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.textbook import RagChunk
from app.services.curriculum_readiness import validate_curriculum_readiness
from app.services.rag_citations import citation_from_chunk, citation_missing_fields
from app.services.reviewed_curriculum_catalog import CANONICAL_CURRICULUM_PATH
from app.services.reviewed_curriculum_metadata import (
    evaluate_chunk_eligibility,
    load_reviewed_curriculum_metadata,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
BOOK_STRUCTURE_PATH = REPO_ROOT / "data/processed/book_structure.json"
LESSON_MAP_PATH = REPO_ROOT / "data/processed/textbook/textbook_lesson_map.reviewed.json"
PAGE_STRUCTURE_PATH = REPO_ROOT / "data/processed/textbook/page_structure.jsonl"
TEXTBOOK_REVIEWED_CHUNKS_PATH = (
    REPO_ROOT
    / "src/data/textbooks/syria_grade_9/reviewed_chunks/textbook_chunks_reviewed.jsonl"
)
SOLUTION_REVIEWED_CHUNKS_PATH = (
    REPO_ROOT / "src/data/processed/solution_book/solution_chunks.cleaned.reviewed.jsonl"
)
DEFAULT_REPORT_DIR = REPO_ROOT / "reports/curriculum_rag_integrity"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object at {path}:{line_number}")
        rows.append(payload)
    return rows


def _normalize_title(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    text = re.sub(r"[\u064b-\u065f\u0670ـ]", "", text)
    text = text.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    return re.sub(r"[\s\-–—]+", " ", text).strip()


def _catalog_lessons(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "unit_id": str(unit.get("stable_id") or ""),
            "unit_number": unit.get("unit_number"),
            "unit_title": unit.get("title_ar"),
            "lesson_id": str(lesson.get("stable_id") or ""),
            "lesson_title": lesson.get("title_ar"),
            "printed_page_start": lesson.get("printed_page_start"),
            "printed_page_end": lesson.get("printed_page_end"),
            "quality_status": lesson.get("quality_status"),
        }
        for unit in catalog.get("units") or []
        if isinstance(unit, dict)
        for chapter in unit.get("chapters") or []
        if isinstance(chapter, dict)
        for lesson in chapter.get("lessons") or []
        if isinstance(lesson, dict)
    ]


def _book_lessons(book_structure: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            **lesson,
            "unit_id": lesson.get("unit_id") or unit.get("unit_id"),
            "unit_title": lesson.get("unit_title") or unit.get("unit_title"),
        }
        for unit in book_structure.get("units") or []
        if isinstance(unit, dict)
        for lesson in unit.get("lessons") or []
        if isinstance(lesson, dict)
    ]


def _duplicates(values: list[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def _artifact_conflicts(
    catalog_lessons: list[dict[str, Any]],
    book_lessons: list[dict[str, Any]],
    mapped_lessons: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    book_by_id = {str(row.get("lesson_id") or ""): row for row in book_lessons}
    map_by_id = {str(row.get("lesson_id") or ""): row for row in mapped_lessons}
    conflicts: list[dict[str, Any]] = []
    for lesson in catalog_lessons:
        lesson_id = lesson["lesson_id"]
        for artifact, candidate in (
            ("book_structure", book_by_id.get(lesson_id)),
            ("textbook_lesson_map", map_by_id.get(lesson_id)),
        ):
            if candidate is None:
                conflicts.append(
                    {"lesson_id": lesson_id, "artifact": artifact, "field": "lesson", "actual": None}
                )
                continue
            checks = {
                "lesson_title": (lesson["lesson_title"], candidate.get("lesson_title")),
                "unit_id": (lesson["unit_id"], candidate.get("unit_id")),
                "printed_page_start": (
                    lesson["printed_page_start"],
                    candidate.get("printed_page_start"),
                ),
                "printed_page_end": (
                    lesson["printed_page_end"],
                    candidate.get("printed_page_end"),
                ),
            }
            for field, (expected, actual) in checks.items():
                matches = (
                    _normalize_title(expected) == _normalize_title(actual)
                    if field == "lesson_title"
                    else expected == actual
                )
                if not matches:
                    conflicts.append(
                        {
                            "lesson_id": lesson_id,
                            "artifact": artifact,
                            "field": field,
                            "expected": expected,
                            "actual": actual,
                        }
                    )
    return conflicts


def _range_issues(lessons: list[dict[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    missing: list[str] = []
    overlaps: list[dict[str, Any]] = []
    by_unit: dict[str, list[dict[str, Any]]] = {}
    for lesson in lessons:
        start = lesson.get("printed_page_start")
        end = lesson.get("printed_page_end")
        if not isinstance(start, int) or not isinstance(end, int) or start > end:
            missing.append(lesson["lesson_id"])
        by_unit.setdefault(lesson["unit_id"], []).append(lesson)
    for unit_id, rows in by_unit.items():
        ordered = sorted(rows, key=lambda row: int(row.get("printed_page_start") or 0))
        for previous, current in zip(ordered, ordered[1:]):
            if int(current["printed_page_start"]) <= int(previous["printed_page_end"]):
                overlaps.append(
                    {
                        "unit_id": unit_id,
                        "first_lesson_id": previous["lesson_id"],
                        "second_lesson_id": current["lesson_id"],
                    }
                )
    return sorted(missing), overlaps


def audit_chunk_integrity(
    db: Session,
    *,
    catalog: dict[str, Any] | None = None,
    reviewed_metadata: dict[str, Any] | None = None,
    reviewed_chunk_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    catalog = catalog or _read_json(CANONICAL_CURRICULUM_PATH)
    reviewed_metadata = reviewed_metadata or load_reviewed_curriculum_metadata(require_ready=False)
    lessons = _catalog_lessons(catalog)
    lessons_by_id = {row["lesson_id"]: row for row in lessons}
    active_version = str(reviewed_metadata.get("version") or "")
    rows = list(db.scalars(select(RagChunk).order_by(RagChunk.id)).all())
    artifact_sources: list[dict[str, Any]] = []
    if reviewed_chunk_rows is None:
        reviewed_chunk_rows = []
        for source_type, path in (
            ("textbook", TEXTBOOK_REVIEWED_CHUNKS_PATH),
            ("solution_book", SOLUTION_REVIEWED_CHUNKS_PATH),
        ):
            source_rows = _read_jsonl(path)
            reviewed_chunk_rows.extend(source_rows)
            artifact_sources.append(
                {
                    "source_type": source_type,
                    "path": str(path.relative_to(REPO_ROOT)),
                    "chunk_count": len(source_rows),
                    "quality_counts": dict(
                        sorted(Counter(str(row.get("quality_status") or "missing") for row in source_rows).items())
                    ),
                }
            )
    else:
        artifact_sources.append(
            {
                "source_type": "injected_test_rows",
                "path": None,
                "chunk_count": len(reviewed_chunk_rows),
                "quality_counts": dict(
                    sorted(
                        Counter(
                            str(row.get("quality_status") or "missing")
                            for row in reviewed_chunk_rows
                        ).items()
                    )
                ),
            }
        )

    artifact_by_id = {
        str(row.get("chunk_id") or ""): row
        for row in reviewed_chunk_rows
        if str(row.get("chunk_id") or "")
    }
    db_by_reviewed_id = {
        str((chunk.metadata_json or {}).get("reviewed_chunk_id") or ""): chunk
        for chunk in rows
        if isinstance(chunk.metadata_json, dict)
        and str(chunk.metadata_json.get("reviewed_chunk_id") or "")
    }
    reviewed_chunk_ids_missing_in_db = sorted(set(artifact_by_id) - set(db_by_reviewed_id))
    db_reviewed_chunk_ids_missing_in_artifacts = sorted(set(db_by_reviewed_id) - set(artifact_by_id))
    content_hash_mismatches: list[dict[str, Any]] = []
    content_text_mismatches: list[str] = []
    for reviewed_chunk_id in sorted(set(artifact_by_id) & set(db_by_reviewed_id)):
        artifact = artifact_by_id[reviewed_chunk_id]
        db_chunk = db_by_reviewed_id[reviewed_chunk_id]
        artifact_metadata = artifact.get("metadata") if isinstance(artifact.get("metadata"), dict) else {}
        artifact_hash = artifact_metadata.get("content_hash")
        db_hash = db_chunk.metadata_json.get("content_hash")
        if artifact_hash != db_hash:
            content_hash_mismatches.append(
                {
                    "reviewed_chunk_id": reviewed_chunk_id,
                    "artifact_content_hash": artifact_hash,
                    "database_content_hash": db_hash,
                }
            )
        artifact_content = str(artifact.get("content") or artifact.get("content_ar") or "")
        if artifact_content != db_chunk.content:
            content_text_mismatches.append(reviewed_chunk_id)

    chunks: list[dict[str, Any]] = []
    lesson_counts: Counter[str] = Counter()
    searchable_count = complete_citations = 0
    invalid_mappings: list[dict[str, Any]] = []
    outside_ranges: list[dict[str, Any]] = []
    legacy_unmapped: list[int] = []
    legacy_unmapped_rows: list[dict[str, Any]] = []

    for chunk in rows:
        decision = evaluate_chunk_eligibility(
            chunk,
            reviewed_metadata,
            legacy=chunk.extraction_method != "reviewed_jsonl",
        )
        citation = citation_from_chunk(chunk)
        lesson_id = str(citation.get("lesson_id") or "")
        lesson = lessons_by_id.get(lesson_id)
        source_type = str(citation.get("source_type") or "")
        legacy = bool(
            decision.normalized_metadata.get("legacy_unmapped")
            or lesson_id.startswith("unmapped:")
        )
        stored_search_allowed = decision.normalized_metadata.get("rag_search_allowed")
        stale = decision.normalized_metadata.get("stale") is True
        version_matches = citation.get("reviewed_metadata_version") == active_version
        embedding_complete = chunk.embedding_status == "completed" and chunk.embedding is not None
        embedding_model_matches = chunk.embedding_model == settings.gemini_embedding_model
        retrieval_eligible = bool(
            decision.rag_search_allowed
            and stored_search_allowed is not False
            and not stale
            and version_matches
            and embedding_complete
            and embedding_model_matches
        )
        effective_reason_codes = list(decision.reason_codes)
        if stored_search_allowed is False:
            effective_reason_codes.append("rag_search_disabled")
        if stale:
            effective_reason_codes.append("stale_chunk")
        if not version_matches:
            effective_reason_codes.append("reviewed_metadata_version_mismatch")
        if not embedding_complete:
            effective_reason_codes.append("embedding_incomplete")
        if not embedding_model_matches:
            effective_reason_codes.append("embedding_model_mismatch")
        missing_citation = citation_missing_fields(citation) if retrieval_eligible else []
        page_status = "source_independent" if source_type == "solution_book" else "unmapped"
        if source_type == "textbook" and lesson is not None:
            start = citation.get("printed_page_start")
            end = citation.get("printed_page_end")
            in_range = (
                isinstance(start, int)
                and isinstance(end, int)
                and int(lesson["printed_page_start"]) <= start <= end <= int(lesson["printed_page_end"])
            )
            page_status = "within_reviewed_lesson" if in_range else "outside_reviewed_lesson"
            if not in_range:
                outside_ranges.append(
                    {
                        "chunk_id": chunk.id,
                        "lesson_id": lesson_id,
                        "chunk_range": [start, end],
                        "lesson_range": [
                            lesson["printed_page_start"],
                            lesson["printed_page_end"],
                        ],
                    }
                )

        if retrieval_eligible:
            searchable_count += 1
            lesson_counts[lesson_id] += 1
            if not missing_citation:
                complete_citations += 1
            if lesson is None and not legacy:
                invalid_mappings.append(
                    {
                        "chunk_id": chunk.id,
                        "lesson_id": lesson_id or None,
                        "unit_id": citation.get("unit_id"),
                        "quality_status": decision.normalized_quality_status,
                    }
                )
        if legacy:
            legacy_unmapped.append(chunk.id)
            legacy_unmapped_rows.append(
                {
                    "chunk_id": chunk.id,
                    "reviewed_chunk_id": (
                        chunk.metadata_json.get("reviewed_chunk_id")
                        if isinstance(chunk.metadata_json, dict)
                        else None
                    ),
                    "unit_id": citation.get("unit_id"),
                    "lesson_id": citation.get("lesson_id"),
                    "printed_page_start": citation.get("printed_page_start"),
                    "printed_page_end": citation.get("printed_page_end"),
                    "content_scope": decision.normalized_metadata.get("content_scope"),
                    "chunk_type": decision.normalized_metadata.get("chunk_type")
                    or chunk.content_type,
                    "quality_status": decision.normalized_quality_status,
                }
            )

        chunks.append(
            {
                "chunk_id": chunk.id,
                "source_id": chunk.source_id,
                "source_type": source_type,
                "unit_id": citation.get("unit_id"),
                "lesson_id": citation.get("lesson_id"),
                "printed_page_start": citation.get("printed_page_start"),
                "printed_page_end": citation.get("printed_page_end"),
                "quality_status": decision.normalized_quality_status,
                "reviewed_metadata_version": citation.get("reviewed_metadata_version"),
                "embedding_status": chunk.embedding_status,
                "embedding_model": chunk.embedding_model,
                "embedding_present": chunk.embedding is not None,
                "stale": stale,
                "contract_rag_search_allowed": decision.rag_search_allowed,
                "stored_rag_search_allowed": stored_search_allowed,
                "rag_search_allowed": retrieval_eligible,
                "warning_required": decision.warning_required,
                "quality_warning": citation.get("quality_warning"),
                "legacy_unmapped": legacy,
                "lesson_mapping_status": (
                    "reviewed" if lesson is not None else "legacy_unmapped" if legacy else "invalid"
                ),
                "page_range_status": page_status,
                "citation_missing_fields": missing_citation,
                "eligibility_reason_codes": list(dict.fromkeys(effective_reason_codes)),
            }
        )

    lessons_without_eligible_chunks = sorted(
        lesson_id for lesson_id in lessons_by_id if lesson_counts[lesson_id] == 0
    )
    incomplete_citations = [
        row for row in chunks if row["rag_search_allowed"] and row["citation_missing_fields"]
    ]
    wrong_version = [
        row["chunk_id"]
        for row in chunks
        if row["rag_search_allowed"] and row["reviewed_metadata_version"] != active_version
    ]
    blocked_searchable = [
        row["chunk_id"]
        for row in chunks
        if row["rag_search_allowed"] and row["quality_status"] == "blocked"
    ]
    errors = (
        len(lessons_without_eligible_chunks)
        + len(invalid_mappings)
        + len(outside_ranges)
        + len(incomplete_citations)
        + len(wrong_version)
        + len(blocked_searchable)
        + len(reviewed_chunk_ids_missing_in_db)
        + len(db_reviewed_chunk_ids_missing_in_artifacts)
        + len(content_hash_mismatches)
        + len(content_text_mismatches)
    )
    warnings = len(legacy_unmapped)
    return {
        "status": "passed" if not errors and not warnings else "passed_with_warnings" if not errors else "failed",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_metadata_version": active_version,
        "embedding_model": "gemini-embedding-001",
        "summary": {
            "total_chunks": len(chunks),
            "searchable_chunks": searchable_count,
            "citation_complete_chunks": complete_citations,
            "citation_completeness_percent": round(
                complete_citations / searchable_count * 100, 2
            ) if searchable_count else 0.0,
            "ready_chunks": sum(row["quality_status"] == "ready" for row in chunks),
            "needs_review_chunks": sum(row["quality_status"] == "needs_review" for row in chunks),
            "blocked_chunks": sum(row["quality_status"] == "blocked" for row in chunks),
            "stale_chunks": sum(row["stale"] for row in chunks),
            "legacy_unmapped_chunks": len(legacy_unmapped),
            "invalid_chunk_mappings": len(invalid_mappings),
            "textbook_chunks_outside_lesson_ranges": len(outside_ranges),
            "lessons_without_eligible_chunks": len(lessons_without_eligible_chunks),
            "errors": errors,
            "warnings": warnings,
        },
        "reviewed_chunk_artifacts": {
            "sources": artifact_sources,
            "artifact_chunk_count": len(reviewed_chunk_rows),
            "artifact_unique_chunk_ids": len(artifact_by_id),
            "database_reviewed_chunk_ids": len(db_by_reviewed_id),
            "reviewed_chunk_ids_missing_in_db": reviewed_chunk_ids_missing_in_db,
            "database_reviewed_chunk_ids_missing_in_artifacts": db_reviewed_chunk_ids_missing_in_artifacts,
            "content_hash_mismatches": content_hash_mismatches,
            "content_text_mismatches": content_text_mismatches,
            "content_changed": bool(content_hash_mismatches or content_text_mismatches),
        },
        "lesson_eligible_chunk_counts": dict(sorted(lesson_counts.items())),
        "lessons_without_eligible_chunks": lessons_without_eligible_chunks,
        "invalid_chunk_mappings": invalid_mappings,
        "textbook_chunks_outside_lesson_ranges": outside_ranges,
        "legacy_unmapped_chunk_ids": legacy_unmapped,
        "legacy_unit_level_review": {
            "status": (
                "accepted_unit_level_needs_review"
                if legacy_unmapped_rows
                and all(row["content_scope"] == "unit_level" for row in legacy_unmapped_rows)
                and all(row["quality_status"] == "needs_review" for row in legacy_unmapped_rows)
                else "not_applicable" if not legacy_unmapped_rows else "manual_review_required"
            ),
            "decision": (
                "Retain without lesson mapping. These reviewed chunks are explicitly unit-level; "
                "assigning a lesson_id would fabricate curriculum metadata."
            ),
            "count": len(legacy_unmapped_rows),
            "by_printed_page": dict(
                sorted(
                    Counter(
                        str(row["printed_page_start"])
                        for row in legacy_unmapped_rows
                    ).items(),
                    key=lambda item: int(item[0]),
                )
            ),
            "by_chunk_type": dict(
                sorted(Counter(str(row["chunk_type"]) for row in legacy_unmapped_rows).items())
            ),
            "rows": legacy_unmapped_rows,
        },
        "wrong_version_searchable_chunk_ids": wrong_version,
        "blocked_searchable_chunk_ids": blocked_searchable,
        "incomplete_citations": incomplete_citations,
        "chunks": chunks,
    }


def audit_curriculum_integrity(
    db: Session,
    *,
    catalog: dict[str, Any] | None = None,
    book_structure: dict[str, Any] | None = None,
    lesson_map: dict[str, Any] | None = None,
    page_structure: list[dict[str, Any]] | None = None,
    reviewed_metadata: dict[str, Any] | None = None,
    chunk_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = catalog or _read_json(CANONICAL_CURRICULUM_PATH)
    book_structure = book_structure or _read_json(BOOK_STRUCTURE_PATH)
    lesson_map = lesson_map or _read_json(LESSON_MAP_PATH)
    page_structure = page_structure or _read_jsonl(PAGE_STRUCTURE_PATH)
    reviewed_metadata = reviewed_metadata or load_reviewed_curriculum_metadata(require_ready=False)
    chunk_report = chunk_report or audit_chunk_integrity(
        db,
        catalog=catalog,
        reviewed_metadata=reviewed_metadata,
    )
    catalog_lessons = _catalog_lessons(catalog)
    book_lessons = _book_lessons(book_structure)
    mapped_lessons = [row for row in lesson_map.get("lessons") or [] if isinstance(row, dict)]
    missing_ranges, overlapping_ranges = _range_issues(catalog_lessons)
    conflicts = _artifact_conflicts(catalog_lessons, book_lessons, mapped_lessons)
    readiness = validate_curriculum_readiness(
        db,
        reviewed_structure=book_structure,
        seed_structure=catalog,
        reviewed_metadata=reviewed_metadata,
    )
    reviewed_ids = {row["lesson_id"] for row in catalog_lessons}
    page_numbers = [
        int(row["printed_page_number"])
        for row in page_structure
        if isinstance(row.get("printed_page_number"), int)
    ]
    unassigned_inside_lesson_range_rows = sorted(
        [
            {
                "printed_page_number": int(row["printed_page_number"]),
                "pdf_page_number": row.get("pdf_page_number"),
                "unit_number": row.get("unit_number"),
                "unit_title": row.get("unit_title"),
                "page_role": row.get("page_role"),
                "lesson_id": row.get("lesson_id"),
                "quality_score": row.get("quality_score"),
            "blocked": row.get("blocked"),
            }
            for row in page_structure
            if isinstance(row.get("printed_page_number"), int)
            and not row.get("lesson_id")
            and any(
                int(lesson["printed_page_start"])
                <= int(row["printed_page_number"])
                <= int(lesson["printed_page_end"])
                for lesson in catalog_lessons
            )
        ],
        key=lambda row: row["printed_page_number"],
    )
    unassigned_inside_lesson_ranges = [
        row["printed_page_number"] for row in unassigned_inside_lesson_range_rows
    ]
    missing_ids = {
        "catalog_unit_ids": sum(not str(unit.get("stable_id") or "") for unit in catalog.get("units") or []),
        "catalog_lesson_ids": sum(not row["lesson_id"] for row in catalog_lessons),
        "book_structure_unit_ids": sum(
            not str(unit.get("unit_id") or "") for unit in book_structure.get("units") or []
        ),
        "book_structure_lesson_ids": sum(not str(row.get("lesson_id") or "") for row in book_lessons),
        "lesson_map_lesson_ids": sum(not str(row.get("lesson_id") or "") for row in mapped_lessons),
    }
    duplicates = {
        "catalog_unit_ids": _duplicates(
            [str(unit.get("stable_id") or "") for unit in catalog.get("units") or []]
        ),
        "catalog_lesson_ids": _duplicates([row["lesson_id"] for row in catalog_lessons]),
        "book_structure_lesson_ids": _duplicates(
            [str(row.get("lesson_id") or "") for row in book_lessons]
        ),
        "lesson_map_lesson_ids": _duplicates(
            [str(row.get("lesson_id") or "") for row in mapped_lessons]
        ),
    }
    errors = (
        readiness.counts.errors
        + sum(missing_ids.values())
        + sum(len(rows) for rows in duplicates.values())
        + len(conflicts)
        + len(missing_ranges)
        + len(overlapping_ranges)
        + int(chunk_report["summary"]["errors"])
    )
    warnings = readiness.counts.warnings + len(unassigned_inside_lesson_ranges)
    return {
        "status": "passed" if not errors and not warnings else "passed_with_warnings" if not errors else "failed",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "description": "Reviewed coverage of the supplied 96-page Chemistry.pdf source",
            "source_pdf_printed_page_start": min(page_numbers) if page_numbers else None,
            "source_pdf_printed_page_end": max(page_numbers) if page_numbers else None,
            "reviewed_unit_numbers": [unit.get("unit_number") for unit in catalog.get("units") or []],
            "does_not_claim_full_grade_book_beyond_source_pdf": True,
        },
        "reviewed_metadata_version": reviewed_metadata.get("version"),
        "reviewed_unit_count": len(catalog.get("units") or []),
        "reviewed_lesson_count": len(catalog_lessons),
        "reviewed_lessons": catalog_lessons,
        "database_counts": readiness.counts.model_dump(),
        "database_lesson_mappings": [row.model_dump() for row in readiness.lesson_mappings],
        "missing_stable_ids": missing_ids,
        "duplicated_stable_ids": duplicates,
        "artifact_conflicts": conflicts,
        "missing_page_ranges": missing_ranges,
        "overlapping_page_ranges": overlapping_ranges,
        "page_structure": {
            "page_count": len(page_structure),
            "printed_page_start": min(page_numbers) if page_numbers else None,
            "printed_page_end": max(page_numbers) if page_numbers else None,
            "unassigned_pages_inside_lesson_ranges": unassigned_inside_lesson_ranges,
            "unassigned_page_details": unassigned_inside_lesson_range_rows,
            "page_191_review_decision": (
                "retain_as_unit_cover_without_lesson_id"
                if any(
                    row["printed_page_number"] == 191
                    and row["page_role"] == "unit_cover"
                    and row["blocked"] is False
                    for row in unassigned_inside_lesson_range_rows
                )
                else "not_verified"
            ),
        },
        "lessons_without_eligible_chunks": chunk_report["lessons_without_eligible_chunks"],
        "reviewed_lesson_ids_with_chunks": sorted(
            reviewed_ids - set(chunk_report["lessons_without_eligible_chunks"])
        ),
        "invalid_chunk_mappings": chunk_report["invalid_chunk_mappings"],
        "textbook_chunks_outside_lesson_ranges": chunk_report[
            "textbook_chunks_outside_lesson_ranges"
        ],
        "legacy_unmapped_chunk_count": chunk_report["summary"]["legacy_unmapped_chunks"],
        "reviewed_data_changed": chunk_report["reviewed_chunk_artifacts"]["content_changed"],
        "reembedding_required": chunk_report["reviewed_chunk_artifacts"]["content_changed"],
        "reembedding_reason": (
            "Reviewed chunk content differs from the indexed database."
            if chunk_report["reviewed_chunk_artifacts"]["content_changed"]
            else "Reviewed chunk content hashes and text match the indexed database; citation mapping does not change embeddings."
        ),
        "errors": errors,
        "warnings": warnings,
    }


def _write_markdown(
    curriculum: dict[str, Any],
    chunks: dict[str, Any],
    report_dir: Path,
) -> tuple[Path, Path]:
    curriculum_path = report_dir / "curriculum_integrity_report.md"
    chunk_path = report_dir / "chunk_integrity_report.md"
    curriculum_lines = [
        "# Curriculum Integrity Report",
        "",
        f"- Status: `{curriculum['status']}`",
        f"- Reviewed metadata: `{curriculum['reviewed_metadata_version']}`",
        f"- Reviewed units: `{curriculum['reviewed_unit_count']}`",
        f"- Reviewed lessons: `{curriculum['reviewed_lesson_count']}`",
        f"- Database units: `{curriculum['database_counts']['database_units']}`",
        f"- Database lessons: `{curriculum['database_counts']['database_lessons']}`",
        f"- Lessons without eligible chunks: `{len(curriculum['lessons_without_eligible_chunks'])}`",
        f"- Invalid chunk mappings: `{len(curriculum['invalid_chunk_mappings'])}`",
        f"- Textbook chunks outside lesson ranges: `{len(curriculum['textbook_chunks_outside_lesson_ranges'])}`",
        f"- Legacy unmapped needs-review chunks: `{curriculum['legacy_unmapped_chunk_count']}`",
        f"- Re-embedding required: `{curriculum['reembedding_required']}`",
        "",
        "## Reviewed Lessons",
        "",
        "| Unit | Unit title | Lesson ID | Lesson title | Printed pages | Quality |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    curriculum_lines.extend(
        f"| {row['unit_id']} | {row['unit_title']} | {row['lesson_id']} | {row['lesson_title']} | "
        f"{row['printed_page_start']}-{row['printed_page_end']} | {row['quality_status']} |"
        for row in curriculum["reviewed_lessons"]
    )
    curriculum_lines.extend(
        [
            "",
            "## Scope Note",
            "",
            "This report proves reviewed coverage for the supplied 96-page source PDF "
            "(printed pages 107-202, units 4-6). It does not claim that units outside "
            "that source PDF were reviewed or ingested.",
            "",
            "## Remaining Warnings",
            "",
            f"- Unassigned pages inside lesson ranges: "
            f"`{curriculum['page_structure']['unassigned_pages_inside_lesson_ranges']}`",
            f"- Legacy unmapped searchable chunks: `{curriculum['legacy_unmapped_chunk_count']}`. "
            "They remain `needs_review` and require a citation warning; they are not promoted to `ready`.",
            f"- Page 191 review decision: "
            f"`{curriculum['page_structure']['page_191_review_decision']}`.",
            f"- Unit-level chunk review decision: "
            f"`{chunks['legacy_unit_level_review']['status']}`.",
            f"- Re-embedding decision: `{curriculum['reembedding_reason']}`",
        ]
    )
    chunk_lines = [
        "# RAG Chunk Integrity Report",
        "",
        f"- Status: `{chunks['status']}`",
        f"- Total chunks: `{chunks['summary']['total_chunks']}`",
        f"- Searchable chunks: `{chunks['summary']['searchable_chunks']}`",
        f"- Citation completeness: `{chunks['summary']['citation_completeness_percent']}%`",
        f"- Ready: `{chunks['summary']['ready_chunks']}`",
        f"- Needs review: `{chunks['summary']['needs_review_chunks']}`",
        f"- Blocked: `{chunks['summary']['blocked_chunks']}`",
        f"- Stale: `{chunks['summary']['stale_chunks']}`",
        f"- Legacy unmapped: `{chunks['summary']['legacy_unmapped_chunks']}`",
        f"- Invalid mappings: `{chunks['summary']['invalid_chunk_mappings']}`",
        f"- Textbook chunks outside lesson ranges: "
        f"`{chunks['summary']['textbook_chunks_outside_lesson_ranges']}`",
        f"- Reviewed artifact chunks: `{chunks['reviewed_chunk_artifacts']['artifact_chunk_count']}`",
        f"- Database reviewed chunk IDs: `{chunks['reviewed_chunk_artifacts']['database_reviewed_chunk_ids']}`",
        f"- Content hash mismatches: `{len(chunks['reviewed_chunk_artifacts']['content_hash_mismatches'])}`",
        f"- Content text mismatches: `{len(chunks['reviewed_chunk_artifacts']['content_text_mismatches'])}`",
        "",
        "## Reviewed Chunk Sources",
        "",
        "| Source type | Path | Chunks | Quality counts |",
        "| --- | --- | ---: | --- |",
    ]
    chunk_lines.extend(
        f"| {source['source_type']} | {source['path']} | {source['chunk_count']} | "
        f"`{json.dumps(source['quality_counts'], ensure_ascii=False, sort_keys=True)}` |"
        for source in chunks["reviewed_chunk_artifacts"]["sources"]
    )
    chunk_lines.extend(
        [
            "",
            "## Eligible Chunks By Lesson",
            "",
            "| Lesson ID | Searchable chunks |",
            "| --- | ---: |",
        ]
    )
    chunk_lines.extend(
        f"| {lesson_id} | {count} |"
        for lesson_id, count in chunks["lesson_eligible_chunk_counts"].items()
        if not lesson_id.startswith("unmapped:")
    )
    chunk_lines.extend(
        [
            "",
            "Solution-book printed pages are validated against the solution-book "
            "source, not against textbook lesson page ranges.",
        ]
    )
    curriculum_path.write_text("\n".join(curriculum_lines) + "\n", encoding="utf-8")
    chunk_path.write_text("\n".join(chunk_lines) + "\n", encoding="utf-8")
    return curriculum_path, chunk_path


def write_integrity_reports(
    db: Session,
    *,
    report_dir: Path = DEFAULT_REPORT_DIR,
) -> dict[str, str]:
    report_dir.mkdir(parents=True, exist_ok=True)
    chunk_report = audit_chunk_integrity(db)
    curriculum_report = audit_curriculum_integrity(db, chunk_report=chunk_report)
    curriculum_json = report_dir / "curriculum_integrity_report.json"
    chunk_json = report_dir / "chunk_integrity_report.json"
    curriculum_json.write_text(
        json.dumps(curriculum_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    chunk_json.write_text(
        json.dumps(chunk_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    curriculum_md, chunk_md = _write_markdown(curriculum_report, chunk_report, report_dir)
    return {
        "curriculum_json": str(curriculum_json),
        "curriculum_markdown": str(curriculum_md),
        "chunk_json": str(chunk_json),
        "chunk_markdown": str(chunk_md),
    }
