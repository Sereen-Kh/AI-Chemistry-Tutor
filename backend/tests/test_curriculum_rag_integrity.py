"""Deterministic curriculum-to-RAG integrity and citation contract tests."""

from __future__ import annotations

import json
from types import SimpleNamespace

from app.core.config import settings
from app.services.curriculum_rag_integrity import audit_chunk_integrity
from app.services.rag_citations import (
    NEEDS_REVIEW_WARNING,
    REQUIRED_CITATION_FIELDS,
    citation_from_chunk,
    citation_missing_fields,
)
from app.services.reviewed_curriculum_catalog import CANONICAL_CURRICULUM_PATH
from app.services.reviewed_curriculum_metadata import load_reviewed_curriculum_metadata


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _ReadOnlySession:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self, _statement):
        return _ScalarRows(self._rows)


def _reviewed_lessons(catalog):
    return [
        (unit, lesson)
        for unit in catalog["units"]
        for chapter in unit["chapters"]
        for lesson in chapter["lessons"]
    ]


def _catalog():
    return json.loads(CANONICAL_CURRICULUM_PATH.read_text(encoding="utf-8"))


def _chunk(
    chunk_id: int,
    unit: dict,
    lesson: dict,
    *,
    source_type: str = "textbook",
    quality_status: str = "ready",
    printed_page: int | None = None,
    reviewed_version: str = "2026-06-reviewed-v1",
    stale: bool = False,
    rag_search_allowed: bool = True,
    embedding_status: str = "completed",
    embedding_model: str | None = None,
):
    page = printed_page or int(lesson["printed_page_start"])
    metadata = {
        "reviewed_chunk_id": f"reviewed-{chunk_id}",
        "content_hash": f"hash-{chunk_id}",
        "source_type": source_type,
        "unit_id": unit["stable_id"],
        "lesson_id": lesson["stable_id"],
        "printed_page_start": page,
        "printed_page_end": page,
        "quality_status": quality_status,
        "reviewed_metadata_version": reviewed_version,
        "stale": stale,
        "rag_search_allowed": rag_search_allowed,
    }
    return SimpleNamespace(
        id=chunk_id,
        source_id=1,
        source="Grade 9 Chemistry",
        source_type=source_type,
        unit_id=None,
        lesson_id=None,
        page_number=page,
        content="محتوى كيميائي مراجع",
        content_type="text",
        extraction_method="reviewed_jsonl",
        metadata_json=metadata,
        embedding=[0.1, 0.2],
        embedding_status=embedding_status,
        embedding_model=embedding_model or settings.gemini_embedding_model,
        similarity_score=0.91,
    )


def _artifact_rows(chunks):
    return [
        {
            "chunk_id": chunk.metadata_json["reviewed_chunk_id"],
            "content": chunk.content,
            "quality_status": chunk.metadata_json["quality_status"],
            "metadata": {"content_hash": chunk.metadata_json["content_hash"]},
        }
        for chunk in chunks
    ]


def test_every_reviewed_lesson_has_an_eligible_chunk_and_complete_citation() -> None:
    catalog = _catalog()
    metadata = load_reviewed_curriculum_metadata(require_ready=False)
    chunks = [
        _chunk(index, unit, lesson)
        for index, (unit, lesson) in enumerate(_reviewed_lessons(catalog), start=1)
    ]

    report = audit_chunk_integrity(
        _ReadOnlySession(chunks),
        catalog=catalog,
        reviewed_metadata=metadata,
        reviewed_chunk_rows=_artifact_rows(chunks),
    )

    assert report["lessons_without_eligible_chunks"] == []
    assert report["textbook_chunks_outside_lesson_ranges"] == []
    assert report["summary"]["citation_completeness_percent"] == 100.0
    assert report["summary"]["searchable_chunks"] == len(chunks)


def test_blocked_stale_wrong_version_and_disabled_chunks_are_excluded() -> None:
    catalog = _catalog()
    metadata = load_reviewed_curriculum_metadata(require_ready=False)
    unit, lesson = _reviewed_lessons(catalog)[0]
    chunks = [
        _chunk(1, unit, lesson, quality_status="blocked"),
        _chunk(2, unit, lesson, stale=True),
        _chunk(3, unit, lesson, reviewed_version="old-version"),
        _chunk(4, unit, lesson, rag_search_allowed=False),
    ]

    report = audit_chunk_integrity(
        _ReadOnlySession(chunks),
        catalog=catalog,
        reviewed_metadata=metadata,
        reviewed_chunk_rows=_artifact_rows(chunks),
    )

    assert report["summary"]["searchable_chunks"] == 0
    assert all(not row["rag_search_allowed"] for row in report["chunks"])
    reasons = {code for row in report["chunks"] for code in row["eligibility_reason_codes"]}
    assert "blocked_quality_status" in reasons
    assert "stale_chunk" in reasons
    assert "reviewed_metadata_version_mismatch" in reasons
    assert "rag_search_disabled" in reasons


def test_needs_review_citation_has_warning_and_all_required_fields() -> None:
    catalog = _catalog()
    unit, lesson = _reviewed_lessons(catalog)[0]
    citation = citation_from_chunk(_chunk(1, unit, lesson, quality_status="needs_review"))

    assert citation_missing_fields(citation) == []
    assert set(REQUIRED_CITATION_FIELDS).issubset(citation)
    assert citation["quality_warning"] == NEEDS_REVIEW_WARNING


def test_textbook_range_is_enforced_but_solution_pages_are_source_independent() -> None:
    catalog = _catalog()
    metadata = load_reviewed_curriculum_metadata(require_ready=False)
    unit, lesson = _reviewed_lessons(catalog)[0]
    outside_page = int(lesson["printed_page_end"]) + 10
    chunks = [
        _chunk(1, unit, lesson, printed_page=outside_page),
        _chunk(2, unit, lesson, source_type="solution_book", printed_page=48),
    ]

    report = audit_chunk_integrity(
        _ReadOnlySession(chunks),
        catalog=catalog,
        reviewed_metadata=metadata,
        reviewed_chunk_rows=_artifact_rows(chunks),
    )

    assert [row["chunk_id"] for row in report["textbook_chunks_outside_lesson_ranges"]] == [1]
    solution = next(row for row in report["chunks"] if row["chunk_id"] == 2)
    assert solution["page_range_status"] == "source_independent"


def test_unmapped_unit_level_chunks_remain_needs_review_without_fabricated_lesson() -> None:
    catalog = _catalog()
    metadata = load_reviewed_curriculum_metadata(require_ready=False)
    unit, lesson = _reviewed_lessons(catalog)[0]
    chunk = _chunk(1, unit, lesson, quality_status="ready")
    chunk.extraction_method = "legacy_pdf"
    chunk.metadata_json.update(
        {
            "lesson_id": "unmapped:textbook:1:1",
            "content_scope": "unit_level",
            "chunk_type": "unit_question",
            "quality_status": "ready",
        }
    )

    report = audit_chunk_integrity(
        _ReadOnlySession([chunk]),
        catalog=catalog,
        reviewed_metadata=metadata,
        reviewed_chunk_rows=_artifact_rows([chunk]),
    )

    reviewed = report["chunks"][0]
    assert reviewed["quality_status"] == "needs_review"
    assert reviewed["warning_required"] is True
    assert reviewed["lesson_mapping_status"] == "legacy_unmapped"
    assert report["legacy_unit_level_review"]["status"] == "accepted_unit_level_needs_review"
