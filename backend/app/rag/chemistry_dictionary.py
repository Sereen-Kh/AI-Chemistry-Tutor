"""Approved chemistry dictionary answers used before broad vector RAG."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from app.rag.arabic_normalizer import normalize_arabic

_DATA_PATH = Path(__file__).with_name("data") / "chemistry_entities.json"


@dataclass(frozen=True)
class ChemistryEntity:
    id: str
    entity_ar: str
    aliases: tuple[str, ...]
    type: str
    answer_ar: str
    formula: str | None
    symbol: str | None
    approved: bool
    grade_level: int
    source_type: str
    confidence: float
    book_validation_terms: tuple[str, ...]


@dataclass(frozen=True)
class DictionaryAnswer:
    intent: str
    entity: ChemistryEntity
    answer: str
    confidence: float


_CACHE: list[ChemistryEntity] | None = None


def load_entities() -> list[ChemistryEntity]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    raw_items = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    _CACHE = [
        ChemistryEntity(
            id=item["id"],
            entity_ar=item["entity_ar"],
            aliases=tuple(item.get("aliases", [])),
            type=item["type"],
            answer_ar=item["answer_ar"],
            formula=item.get("formula"),
            symbol=item.get("symbol"),
            approved=bool(item.get("approved", False)),
            grade_level=int(item.get("grade_level", 9)),
            source_type=item.get("source_type", "teacher_dictionary"),
            confidence=float(item.get("confidence", 0.9)),
            book_validation_terms=tuple(item.get("book_validation_terms", [])),
        )
        for item in raw_items
    ]
    return _CACHE


def approved_entities() -> list[ChemistryEntity]:
    return [entity for entity in load_entities() if entity.approved and entity.grade_level == 9]


def find_entity(question: str) -> ChemistryEntity | None:
    normalized = normalize_arabic(question).lower()
    candidates = sorted(approved_entities(), key=lambda item: len(item.entity_ar), reverse=True)
    for entity in candidates:
        for alias in entity.aliases:
            normalized_alias = normalize_arabic(alias).lower()
            if normalized_alias and normalized_alias in normalized:
                return entity
    return None


def answer_from_dictionary(question: str, intent: str) -> DictionaryAnswer | None:
    entity = find_entity(question)
    if entity is None:
        return None

    if intent == "formula_lookup":
        if entity.formula:
            return DictionaryAnswer(
                intent=intent,
                entity=entity,
                answer=f"الصيغة الكيميائية لـ {entity.entity_ar} هي {entity.formula}.",
                confidence=entity.confidence,
            )
        if entity.symbol:
            return DictionaryAnswer(
                intent=intent,
                entity=entity,
                answer=f"رمز {entity.entity_ar} هو {entity.symbol}.",
                confidence=entity.confidence,
            )
        return None

    if intent in {"definition_lookup", "property_lookup", "general_explanation"} and entity.answer_ar:
        return DictionaryAnswer(
            intent="property_lookup" if entity.type == "property" else "definition_lookup",
            entity=entity,
            answer=entity.answer_ar,
            confidence=entity.confidence,
        )

    return None

