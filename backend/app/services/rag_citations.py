"""Shared citation mapping for student-facing RAG responses."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


REQUIRED_CITATION_FIELDS = (
    "chunk_id",
    "source_id",
    "source_type",
    "printed_page_start",
    "printed_page_end",
    "unit_id",
    "lesson_id",
    "quality_status",
    "reviewed_metadata_version",
    "score",
)

NEEDS_REVIEW_WARNING = "This source is marked needs_review."


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _first(*values: Any) -> Any:
    return next((value for value in values if value not in (None, "", [])), None)


def reviewed_chunk_metadata(chunk: Any) -> dict[str, Any]:
    """Merge stored metadata while preferring reviewed stable identifiers."""

    metadata = {
        **_dict(_value(chunk, "metadata_json")),
        **_dict(_value(chunk, "curriculum_metadata")),
    }
    page_number = _value(chunk, "page_number")
    return {
        **metadata,
        "source_type": _first(metadata.get("source_type"), _value(chunk, "source_type")),
        "unit_id": _first(metadata.get("unit_id"), _value(chunk, "unit_id")),
        "lesson_id": _first(
            metadata.get("lesson_id"),
            metadata.get("linked_textbook_lesson_id"),
            _value(chunk, "lesson_id"),
        ),
        "printed_page_start": _first(
            metadata.get("printed_page_start"),
            metadata.get("page_start"),
            _value(chunk, "printed_page_start"),
            page_number,
        ),
        "printed_page_end": _first(
            metadata.get("printed_page_end"),
            metadata.get("page_end"),
            _value(chunk, "printed_page_end"),
            page_number,
        ),
        "quality_status": _first(metadata.get("quality_status"), _value(chunk, "quality_status")),
        "reviewed_metadata_version": _first(
            metadata.get("reviewed_metadata_version"),
            _value(chunk, "reviewed_metadata_version"),
        ),
    }


def citation_from_chunk(chunk: Any) -> dict[str, Any]:
    """Build the canonical citation plus compatibility fields used by clients."""

    metadata = reviewed_chunk_metadata(chunk)
    quality_status = metadata.get("quality_status")
    quality_warning = _first(_value(chunk, "quality_warning"), metadata.get("quality_warning"))
    if quality_status == "needs_review" and not quality_warning:
        quality_warning = NEEDS_REVIEW_WARNING
    source = _value(chunk, "source")
    if source is not None and not isinstance(source, str):
        source = getattr(source, "title", None)
    score = float(_first(_value(chunk, "similarity_score"), _value(chunk, "score"), 0.0))
    page_number = _value(chunk, "page_number")
    content_type = _first(_value(chunk, "content_type"), _value(chunk, "chunk_type"), "text")
    content = str(_first(_value(chunk, "content"), _value(chunk, "content_ar"), "")).strip()

    return {
        "chunk_id": _first(_value(chunk, "chunk_id"), _value(chunk, "id")),
        "source_id": _value(chunk, "source_id"),
        "source": source,
        "source_type": metadata.get("source_type"),
        "page_number": page_number,
        "printed_page_start": metadata.get("printed_page_start"),
        "printed_page_end": metadata.get("printed_page_end"),
        "unit_id": metadata.get("unit_id"),
        "lesson_id": metadata.get("lesson_id"),
        "content_type": content_type,
        "content_preview": content[:240] or None,
        "quality_status": quality_status,
        "quality_warning": quality_warning,
        "reviewed_metadata_version": metadata.get("reviewed_metadata_version"),
        "score": round(score, 4),
        "similarity_score": round(score, 4),
        "curriculum_metadata": metadata,
    }


def citations_from_chunks(chunks: Iterable[Any]) -> list[dict[str, Any]]:
    return [citation_from_chunk(chunk) for chunk in chunks]


def citation_missing_fields(citation: dict[str, Any]) -> list[str]:
    return [
        field
        for field in REQUIRED_CITATION_FIELDS
        if citation.get(field) in (None, "", [])
    ]


def source_block_from_chunk(chunk: Any) -> dict[str, Any]:
    citation = citation_from_chunk(chunk)
    return {
        "book_id": citation.get("source"),
        "page": citation.get("page_number"),
        "chunk_id": citation["chunk_id"],
        "chunk_type": citation["content_type"],
        "content_preview": citation["content_preview"],
        "score": citation["score"],
        "source_id": citation["source_id"],
        "source_type": citation["source_type"],
        "printed_page_start": citation["printed_page_start"],
        "printed_page_end": citation["printed_page_end"],
        "unit_id": citation["unit_id"],
        "lesson_id": citation["lesson_id"],
        "quality_status": citation["quality_status"],
        "quality_warning": citation["quality_warning"],
        "reviewed_metadata_version": citation["reviewed_metadata_version"],
        "curriculum_metadata": citation["curriculum_metadata"],
    }


def source_blocks_from_chunks(chunks: Iterable[Any]) -> list[dict[str, Any]]:
    return [source_block_from_chunk(chunk) for chunk in chunks]
