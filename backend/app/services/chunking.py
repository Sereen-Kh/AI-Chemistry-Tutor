"""Chunking and text merge helpers for Arabic RAG content."""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import re

DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 180


@dataclass(frozen=True)
class ChunkRecord:
    """A retrievable chunk plus content and source metadata."""

    content: str
    content_type: str
    metadata: dict


def split_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
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
    """Normalize Arabic text lightly for retrieval matching."""
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


def section_text(section: dict) -> str:
    """Format one structured section as retrievable text."""
    heading = section.get("heading")
    content = section.get("content") or ""
    return f"{heading}\n{content}".strip() if heading else content.strip()


def normalize_paragraph_for_dedupe(text: str) -> str:
    """Normalize a paragraph for duplicate detection without changing stored text."""
    normalized = normalize_arabic(text)
    normalized = re.sub(r"\s+([،؛؟.!:])", r"\1", normalized)
    normalized = re.sub(r"([،؛؟.!:])(?=\S)", r"\1 ", normalized)
    return normalized.strip()


def deduplicate_sections(sections: list[dict], similarity_threshold: float = 0.92) -> list[dict]:
    """Remove obvious repeated paragraphs while keeping the first source copy."""
    kept: list[dict] = []
    fingerprints: list[str] = []
    for section in sections:
        content = section_text(section)
        if not content:
            continue
        fingerprint = normalize_paragraph_for_dedupe(content)
        duplicate = any(
            fingerprint == existing
            or difflib.SequenceMatcher(a=fingerprint, b=existing).ratio() >= similarity_threshold
            for existing in fingerprints
        )
        if duplicate:
            continue
        kept.append(section)
        fingerprints.append(fingerprint)
    return kept


def _append_unique_chunk(records: list[ChunkRecord], fingerprints: set[str], record: ChunkRecord) -> None:
    content = record.content.strip()
    if not content:
        return
    fingerprint = normalize_paragraph_for_dedupe(content)
    if not fingerprint or fingerprint in fingerprints:
        return
    fingerprints.add(fingerprint)
    records.append(record)


def _question_text(question: dict) -> str:
    parts = [str(question.get("question_text") or "").strip()]
    options = question.get("options") or []
    if isinstance(options, list) and options:
        parts.append("الخيارات:")
        parts.extend(f"- {option}" for option in options if str(option).strip())
    correct_answer = question.get("correct_answer")
    answer_source = question.get("answer_source")
    if correct_answer and answer_source in {"page", "answer_key"}:
        parts.append(f"الإجابة الرسمية: {correct_answer}")
    explanation = question.get("explanation")
    if explanation:
        parts.append(f"الشرح: {explanation}")
    return "\n".join(part for part in parts if part)


def _diagram_text(diagram: dict) -> str:
    labels = diagram.get("labels") or []
    labels_text = "، ".join(str(label) for label in labels if str(label).strip())
    parts = [
        diagram.get("title"),
        diagram.get("description"),
        f"الملصقات: {labels_text}" if labels_text else None,
        diagram.get("related_text"),
    ]
    return "\n".join(str(part).strip() for part in parts if str(part or "").strip())


def _equation_text(equation: dict) -> str:
    parts = [equation.get("equation"), equation.get("description")]
    return "\n".join(str(part).strip() for part in parts if str(part or "").strip())


def _table_text(table: dict) -> str:
    title = table.get("title")
    markdown = table.get("markdown")
    return "\n\n".join(str(part).strip() for part in [title, markdown] if str(part or "").strip())


def build_page_chunk_records(
    page_payload: dict,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[ChunkRecord]:
    """Build section-aware, atomic RAG chunks from one cached page payload.

    Structured items become dedicated chunks. Free text is split only inside its
    own page section; tables, equations, diagrams, and questions stay atomic.
    """
    records: list[ChunkRecord] = []
    fingerprints: set[str] = set()
    base_metadata = {
        "page_type": page_payload.get("page_type") or page_payload.get("classification"),
        "page_status": page_payload.get("status"),
        "extraction_methods": page_payload.get("extraction_methods") or [],
        "warnings": page_payload.get("warnings") or [],
        "completeness_score": page_payload.get("completeness_score"),
    }

    for section_index, section in enumerate(page_payload.get("sections") or []):
        content = section_text(section)
        content_type = section.get("content_type") or "text"
        for split_index, chunk in enumerate(split_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)):
            _append_unique_chunk(
                records,
                fingerprints,
                ChunkRecord(
                    content=chunk,
                    content_type=content_type,
                    metadata={
                        **base_metadata,
                        "chunk_role": "section",
                        "section_index": section_index,
                        "section_heading": section.get("heading"),
                        "split_index": split_index,
                    },
                ),
            )

    for table_index, table in enumerate(page_payload.get("tables") or []):
        content = _table_text(table)
        _append_unique_chunk(
            records,
            fingerprints,
            ChunkRecord(
                content=content,
                content_type="table",
                metadata={
                    **base_metadata,
                    "chunk_role": "table",
                    "table_index": table_index,
                    "table_title": table.get("title"),
                },
            ),
        )

    for diagram_index, diagram in enumerate(page_payload.get("diagrams") or []):
        content = _diagram_text(diagram)
        _append_unique_chunk(
            records,
            fingerprints,
            ChunkRecord(
                content=content,
                content_type="diagram",
                metadata={
                    **base_metadata,
                    "chunk_role": "diagram",
                    "diagram_index": diagram_index,
                    "diagram_title": diagram.get("title"),
                },
            ),
        )

    for equation_index, equation in enumerate(page_payload.get("equations") or []):
        content = _equation_text(equation)
        _append_unique_chunk(
            records,
            fingerprints,
            ChunkRecord(
                content=content,
                content_type="equation",
                metadata={
                    **base_metadata,
                    "chunk_role": "equation",
                    "equation_index": equation_index,
                },
            ),
        )

    for question_index, question in enumerate(page_payload.get("questions") or []):
        content = _question_text(question)
        _append_unique_chunk(
            records,
            fingerprints,
            ChunkRecord(
                content=content,
                content_type="exercise",
                metadata={
                    **base_metadata,
                    "chunk_role": "question",
                    "question_index": question_index,
                    "question_type": question.get("question_type") or "unknown",
                    "answer_source": question.get("answer_source") or "unknown",
                },
            ),
        )

    if records:
        return records

    fallback_content = (
        page_payload.get("raw_markdown")
        or page_payload.get("merged_content")
        or page_payload.get("text_layer_content")
        or page_payload.get("raw_text")
        or ""
    )
    for split_index, chunk in enumerate(split_text(str(fallback_content), chunk_size=chunk_size, chunk_overlap=chunk_overlap)):
        _append_unique_chunk(
            records,
            fingerprints,
            ChunkRecord(
                content=chunk,
                content_type="full_page",
                metadata={**base_metadata, "chunk_role": "full_page_fallback", "split_index": split_index},
            ),
        )
    return records
