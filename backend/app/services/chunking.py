"""Chunking and text merge helpers for Arabic RAG content."""

from __future__ import annotations

import difflib
import re


def split_text(text: str, chunk_size: int = 650, chunk_overlap: int = 90) -> list[str]:
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
