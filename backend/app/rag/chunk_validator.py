"""Validate retrieved chunks before using them as answer evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.rag.arabic_normalizer import normalize_arabic


class ChunkLike(Protocol):
    id: int
    page_number: int | None
    content: str
    content_type: str
    similarity_score: float


@dataclass(frozen=True)
class ChunkValidation:
    chunk_id: int
    page: int | None
    score: float
    valid_for_answer: bool
    rejection_reason: str | None
    preview: str


def validate_chunk(question: str, chunk: ChunkLike, *, entity: str | None = None, intent: str | None = None) -> ChunkValidation:
    question_norm = normalize_arabic(question).lower()
    content_norm = normalize_arabic(chunk.content).lower()
    reason: str | None = None

    entity_norm = normalize_arabic(entity or "").lower()
    if entity_norm in {"الماء", "ماء"} and not any(term in content_norm for term in ("h2o", "صيغه الماء", "جزيء ماء")):
        reason = "water mention is not direct evidence for water"
    elif entity_norm in {"الحموض", "الاحماض"} and not any(term in content_norm for term in ("h+", "ايونات الهدروجين", "ايونات الهيدروجين")):
        reason = "acid chunk lacks H+ or hydrogen-ion evidence"
    elif entity_norm in {"الاسس", "الأسس", "القواعد"} and not any(term in content_norm for term in ("oh-", "ايونات الهدروكسيد")):
        reason = "base chunk lacks OH- or hydroxide evidence"
    elif "عباد الشمس" in question_norm:
        expected = "الاحمر" if any(term in question_norm for term in ("حمضي", "حمض")) else "الازرق"
        if "عباد الشمس" not in content_norm or expected not in content_norm:
            reason = "litmus chunk lacks expected indicator color"
    elif intent in {"reaction_lookup", "reaction_query"}:
        if not any(token in content_norm for token in ("تفاعل", "معادله", "النشاط", "cu", "h2so4", "hcl")):
            reason = "reaction chunk lacks reactants or reaction rule"

    return ChunkValidation(
        chunk_id=chunk.id,
        page=chunk.page_number,
        score=round(float(chunk.similarity_score), 4),
        valid_for_answer=reason is None,
        rejection_reason=reason,
        preview=chunk.content[:180].replace("\n", " ").strip(),
    )


def validate_chunks(question: str, chunks: list[ChunkLike], *, entity: str | None = None, intent: str | None = None) -> list[ChunkValidation]:
    return [validate_chunk(question, chunk, entity=entity, intent=intent) for chunk in chunks]

