"""Chunking and text merge helpers for Arabic RAG content."""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import re

DEFAULT_CHUNK_SIZE = 900
DEFAULT_CHUNK_OVERLAP = 180

_ARABIC_BULLET_RE = re.compile(r"^\s*(?:[-*•]|[\u0660-\u0669\d]+[.)-])\s*")
_FORMULA_TOKEN_RE = re.compile(
    r"\b(?:[A-Z][a-z]?(?:[0-9₀-₉]+)?|\([A-Za-z0-9₀-₉+\-⁺⁻]+\)[0-9₀-₉]*){1,8}[+\-⁺⁻]?\b|"
    r"\b(?:H\+|H⁺|OH-|OH⁻)\b"
)
_SUBSCRIPT_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SUPERSCRIPT_CHARGES = str.maketrans({"⁺": "+", "⁻": "-"})
_SUMMARY_HEADINGS = ("استنتج", "تعلمت", "نتيجه", "نتيجة")
_DEFINITION_MARKERS = ("مواد", "هي", "تعطي", "تتفكك", "تتاين", "تتأين", "عباره عن", "فرع من")
_NOISY_OCR_MARKERS = ("| --- |", "\u0007", "ﺗﻌﻠﻤﺖ", "اﻫﺪاف")


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


def normalize_formula(formula: str) -> str:
    """Normalize chemistry formula glyphs used by OCR/Gemini outputs."""
    return formula.translate(_SUBSCRIPT_DIGITS).translate(_SUPERSCRIPT_CHARGES).replace(" ", "")


def extract_formula_terms(text: str) -> list[str]:
    """Extract stable chemistry formula terms from Arabic/OCR text."""
    formulas: set[str] = set()
    for match in _FORMULA_TOKEN_RE.findall(text or ""):
        normalized = normalize_formula(match)
        if len(normalized) < 2:
            continue
        if normalized.lower() in {"ml", "mol", "aq", "g", "l", "s"}:
            continue
        formulas.add(normalized)
    return sorted(formulas)


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


def _section_kind(section: dict) -> str:
    heading = normalize_arabic(str(section.get("heading") or "")).lower()
    declared_type = str(section.get("content_type") or section.get("type") or "text").strip() or "text"
    content = normalize_arabic(str(section.get("content") or "")).lower()

    if declared_type in {"exercise", "question"}:
        return "exercise"
    if declared_type in {"table", "diagram", "equation", "definition", "result", "objective"}:
        return declared_type
    if "هدف" in heading or "اهداف" in heading:
        return "objective"
    if any(term in heading for term in _SUMMARY_HEADINGS):
        return "learned_summary" if "تعلم" in heading else "result"
    if ":" in section_text(section) and any(marker in content for marker in _DEFINITION_MARKERS):
        return "definition"
    return declared_type


def _atomic_fact_lines(content: str) -> list[str]:
    """Split short bullet/result lists into retrievable educational facts."""
    cleaned_lines = [line.strip() for line in str(content or "").splitlines()]
    facts: list[str] = []
    current: list[str] = []
    for line in cleaned_lines:
        if not line:
            continue
        is_bullet = bool(_ARABIC_BULLET_RE.match(line))
        stripped = _ARABIC_BULLET_RE.sub("", line).strip()
        if is_bullet and current:
            facts.append(" ".join(current).strip())
            current = [stripped]
        elif is_bullet:
            current = [stripped]
        elif current and len(" ".join(current)) < 220:
            current.append(stripped)
        elif current:
            facts.append(" ".join(current).strip())
            current = [stripped]
        else:
            current = [stripped]
    if current:
        facts.append(" ".join(current).strip())
    return [fact for fact in facts if 24 <= len(fact) <= 420]


def _chunk_content_type(base_type: str, content: str) -> str:
    normalized = normalize_arabic(content)
    if base_type in {"learned_summary", "result", "text"} and ":" in content:
        if any(marker in normalized for marker in ("مواد", "هي", "احد فروع", "هو عدد", "تفاعلات")):
            return "definition"
    if base_type == "text" and any(marker in normalized for marker in ("اكتب", "احسب", "اختر", "اكمل")):
        return "exercise"
    return base_type


def _with_content_metadata(metadata: dict, content: str) -> dict:
    formulas = extract_formula_terms(content)
    if not formulas:
        return metadata
    return {**metadata, "formulas": formulas}


def _is_noisy_aggregate_section(section: dict, has_clean_sections: bool) -> bool:
    if not has_clean_sections or section.get("heading"):
        return False
    content = str(section.get("content") or "")
    if len(content) < 450:
        return False
    if any(marker in content for marker in _NOISY_OCR_MARKERS):
        return True
    return bool(re.search(r"\n\s*[A-Z]\s*\n\s*[0-9₀-₉]", content))


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

    sections = list(page_payload.get("sections") or [])
    has_clean_sections = any(section.get("heading") and str(section.get("content") or "").strip() for section in sections)

    for section_index, section in enumerate(sections):
        if _is_noisy_aggregate_section(section, has_clean_sections):
            continue
        content = section_text(section)
        content_type = _section_kind(section)
        atomic_lines = _atomic_fact_lines(content) if content_type in {"learned_summary", "result", "definition"} else []
        chunks = atomic_lines or split_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        for split_index, chunk in enumerate(chunks):
            chunk_type = _chunk_content_type(content_type, chunk)
            _append_unique_chunk(
                records,
                fingerprints,
                ChunkRecord(
                    content=chunk,
                    content_type=chunk_type,
                    metadata=_with_content_metadata({
                        **base_metadata,
                        "chunk_role": "section",
                        "section_index": section_index,
                        "section_heading": section.get("heading"),
                        "split_index": split_index,
                        "atomic_fact": bool(atomic_lines),
                    }, chunk),
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
                metadata=_with_content_metadata({
                    **base_metadata,
                    "chunk_role": "table",
                    "table_index": table_index,
                    "table_title": table.get("title"),
                }, content),
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
                metadata=_with_content_metadata({
                    **base_metadata,
                    "chunk_role": "diagram",
                    "diagram_index": diagram_index,
                    "diagram_title": diagram.get("title"),
                }, content),
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
                metadata=_with_content_metadata({
                    **base_metadata,
                    "chunk_role": "equation",
                    "equation_index": equation_index,
                }, content),
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
                metadata=_with_content_metadata({
                    **base_metadata,
                    "chunk_role": "question",
                    "question_index": question_index,
                    "question_type": question.get("question_type") or "unknown",
                    "answer_source": question.get("answer_source") or "unknown",
                }, content),
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
                metadata=_with_content_metadata(
                    {**base_metadata, "chunk_role": "full_page_fallback", "split_index": split_index},
                    chunk,
                ),
            ),
        )
    return records
