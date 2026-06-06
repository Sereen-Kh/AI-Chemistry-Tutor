"""Small verified textbook knowledge layer used before broad vector retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from app.rag.arabic_normalizer import normalize_arabic


@dataclass(frozen=True)
class BookKnowledgeAnswer:
    key: str
    intent: str
    answer: str
    page_numbers: list[int]
    confidence: float = 0.92
    source_type: str = "book_knowledge"


_BOOK_KNOWLEDGE = (
    BookKnowledgeAnswer(
        key="acids_definition",
        intent="definition_lookup",
        answer="الحموض مواد تعطي عند انحلالها في الماء أيونات الهدروجين H⁺.",
        page_numbers=[11],
    ),
    BookKnowledgeAnswer(
        key="bases_definition",
        intent="definition_lookup",
        answer="الأسس مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻.",
        page_numbers=[19],
    ),
    BookKnowledgeAnswer(
        key="acidic_litmus",
        intent="property_lookup",
        answer="تتلون المحاليل الحمضية ورقة عباد الشمس باللون الأحمر.",
        page_numbers=[13],
    ),
    BookKnowledgeAnswer(
        key="basic_litmus",
        intent="property_lookup",
        answer="تتلون المحاليل الأساسية ورقة عباد الشمس باللون الأزرق.",
        page_numbers=[23],
    ),
    BookKnowledgeAnswer(
        key="cao_water",
        intent="equation_lookup",
        answer="معادلة تفاعل أكسيد الكالسيوم مع الماء هي:\nCaO + H₂O → Ca(OH)₂",
        page_numbers=[41],
        confidence=0.95,
        source_type="equation",
    ),
)


def answer_from_book_knowledge(question: str, intent: str | None = None) -> BookKnowledgeAnswer | None:
    normalized = normalize_arabic(question).lower()
    if "cao" in normalized or ("اكسيد الكالسيوم" in normalized and "ماء" in normalized):
        return next(item for item in _BOOK_KNOWLEDGE if item.key == "cao_water")
    if "عباد الشمس" in normalized and any(term in normalized for term in ("حمضي", "حمض", "الحموض")):
        return next(item for item in _BOOK_KNOWLEDGE if item.key == "acidic_litmus")
    if "عباد الشمس" in normalized and any(term in normalized for term in ("اساسي", "الاسس", "قاعد")):
        return next(item for item in _BOOK_KNOWLEDGE if item.key == "basic_litmus")
    if intent == "definition_lookup" and any(term in normalized for term in ("الحموض", "الاحماض")):
        return next(item for item in _BOOK_KNOWLEDGE if item.key == "acids_definition")
    if intent == "definition_lookup" and any(term in normalized for term in ("الاسس", "القواعد")):
        return next(item for item in _BOOK_KNOWLEDGE if item.key == "bases_definition")
    return None

