"""Deterministic routing for short Arabic chemistry questions before generic RAG."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from app.core.config import PROJECT_DIR

_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_TATWEEL_RE = re.compile(r"\u0640+")

_SUBSCRIPT_TRANSLATION = str.maketrans(
    {
        "₀": "0",
        "₁": "1",
        "₂": "2",
        "₃": "3",
        "₄": "4",
        "₅": "5",
        "₆": "6",
        "₇": "7",
        "₈": "8",
        "₉": "9",
    }
)

_ARABIC_DIGITS_TRANSLATION = str.maketrans(
    {
        "٠": "0",
        "١": "1",
        "٢": "2",
        "٣": "3",
        "٤": "4",
        "٥": "5",
        "٦": "6",
        "٧": "7",
        "٨": "8",
        "٩": "9",
    }
)


@dataclass(frozen=True)
class RoutedAnswer:
    """A direct answer produced before generic RAG retrieval."""

    intent: str
    answer: str
    confidence: float
    page_numbers: list[int]
    suggested_next_action: str | None = None


_CHEMISTRY_FACTS = [
    {
        "entity": "الماء",
        "aliases": ["الماء", "ماء", "h2o", "h₂o"],
        "formula": "H₂O",
        "formula_ascii": "H2O",
        "pages": [30],
        "kind": "formula",
    },
    {
        "entity": "حمض كلور الماء",
        "aliases": ["حمض كلور الماء", "كلور الماء", "hcl"],
        "formula": "HCl",
        "formula_ascii": "HCl",
        "pages": [5, 11, 17],
        "kind": "formula",
    },
    {
        "entity": "حمض الكبريت",
        "aliases": ["حمض الكبريت", "h2so4", "h₂so₄"],
        "formula": "H₂SO₄",
        "formula_ascii": "H2SO4",
        "pages": [9, 11, 13],
        "kind": "formula",
    },
    {
        "entity": "هيدروكسيد الصوديوم",
        "aliases": ["هيدروكسيد الصوديوم", "هدروكسيد الصوديوم", "naoh"],
        "formula": "NaOH",
        "formula_ascii": "NaOH",
        "pages": [6, 19, 21, 41],
        "kind": "formula",
    },
    {
        "entity": "حمض الخل",
        "aliases": ["حمض الخل", "ch3cooh", "ch₃cooh"],
        "formula": "CH₃COOH",
        "formula_ascii": "CH3COOH",
        "pages": [11, 13, 17],
        "kind": "formula",
    },
]

_WATER_DECOMPOSITION = {
    "answer": (
        "معادلة تفكك الماء في وعاء فولتا هي:\n"
        "2H₂O(l) → 2H₂(g) + O₂(g)\n\n"
        "ينتج عن التفكك غاز الهدروجين وغاز الأكسجين."
    ),
    "pages": [30],
}


def normalize_query(text: str) -> str:
    """Normalize Arabic and chemistry notation for rule-based intent matching."""
    normalized = text.lower().translate(_SUBSCRIPT_TRANSLATION).translate(_ARABIC_DIGITS_TRANSLATION)
    normalized = _DIACRITICS_RE.sub("", normalized)
    normalized = _TATWEEL_RE.sub("", normalized)
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ؤ": "و",
        "ئ": "ي",
        "ى": "ي",
        "ة": "ه",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _contains_any(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _find_fact(query: str) -> dict | None:
    normalized = normalize_query(query)
    for fact in _CHEMISTRY_FACTS:
        for alias in fact["aliases"]:
            if normalize_query(alias) in normalized:
                return fact
    return None


def _answer_formula(query: str) -> RoutedAnswer | None:
    normalized = normalize_query(query)
    if not _contains_any(normalized, ("رمز", "صيغه", "الصيغه", "formula", "فورمولا")):
        return None
    fact = _find_fact(query)
    if not fact:
        return None
    answer = (
        f"الصيغة الكيميائية لـ {fact['entity']} هي: {fact['formula']}.\n\n"
        f"كتابة عادية: {fact['formula_ascii']}."
    )
    return RoutedAnswer(
        intent="formula_lookup",
        answer=answer,
        confidence=1.0,
        page_numbers=list(fact["pages"]),
        suggested_next_action="يمكنك أن تسأل عن معنى الصيغة أو عن معادلة تفاعل مرتبطة بها.",
    )


def _answer_water_equation(query: str) -> RoutedAnswer | None:
    normalized = normalize_query(query)
    if "معادله" not in normalized or "ماء" not in normalized:
        return None
    if _contains_any(normalized, ("تفكك", "تحليل", "فولتا")):
        return RoutedAnswer(
            intent="equation_lookup",
            answer=_WATER_DECOMPOSITION["answer"],
            confidence=1.0,
            page_numbers=list(_WATER_DECOMPOSITION["pages"]),
            suggested_next_action="يمكنك أن تسأل عن سبب ظهور غازي الهدروجين والأكسجين.",
        )
    if _contains_any(normalized, ("تاين", "تأين", "ايوني", "شارد")):
        return RoutedAnswer(
            intent="clarification",
            answer=(
                "هل تقصد تأين الماء أم تفكك الماء؟\n\n"
                "- الصيغة الكيميائية للماء: H₂O\n"
                "- تفكك الماء في وعاء فولتا: 2H₂O → 2H₂ + O₂\n"
                "- تأين الماء يكتب عادة: H₂O ⇌ H⁺ + OH⁻"
            ),
            confidence=0.9,
            page_numbers=[],
            suggested_next_action="اكتب: تفكك الماء، أو تأين الماء، أو صيغة الماء.",
        )
    return RoutedAnswer(
        intent="clarification",
        answer=(
            "سؤالك عن \"معادلة الماء\" غير محدد.\n\n"
            "هل تقصد:\n"
            "1. الصيغة الكيميائية للماء: H₂O\n"
            "2. معادلة تفكك الماء: 2H₂O → 2H₂ + O₂\n"
            "3. تأين الماء: H₂O ⇌ H⁺ + OH⁻"
        ),
        confidence=0.9,
        page_numbers=[],
        suggested_next_action="حدد هل تريد الصيغة، التفكك، أم التأين.",
    )


def _book_structure_path(source_slug: str = "syria_grade_9_chemistry") -> Path:
    return PROJECT_DIR / "data" / "textbooks" / source_slug / "book_structure.json"


def load_book_structure(source_slug: str = "syria_grade_9_chemistry") -> dict:
    path = _book_structure_path(source_slug)
    if not path.exists():
        return {"lessons": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _lesson_number(query: str) -> int | None:
    normalized = normalize_query(query)
    ordinal_map = {
        "اول": 1,
        "الاول": 1,
        "ثاني": 2,
        "الثاني": 2,
        "ثالث": 3,
        "الثالث": 3,
        "رابع": 4,
        "الرابع": 4,
        "خامس": 5,
        "الخامس": 5,
    }
    number_match = re.search(r"(?:درس|الدرس)\s*(\d+)", normalized)
    if number_match:
        return int(number_match.group(1))
    for word, number in ordinal_map.items():
        if f"درس {word}" in normalized or f"الدرس {word}" in normalized:
            return number
    return None


def _answer_lesson_navigation(query: str) -> RoutedAnswer | None:
    normalized = normalize_query(query)
    if "درس" not in normalized:
        return None
    lesson_no = _lesson_number(query)
    if lesson_no is None:
        return None
    structure = load_book_structure()
    lesson = next((item for item in structure.get("lessons", []) if item.get("lesson_no") == lesson_no), None)
    if not lesson:
        return None

    objectives = "\n".join(f"- {item}" for item in lesson.get("objectives", []))
    keywords = "، ".join(lesson.get("keywords", []))
    answer = (
        f"الدرس {lesson_no}: {lesson['title']}.\n\n"
        "يحتوي الدرس على:\n"
        f"{objectives}\n\n"
        f"الكلمات المفتاحية: {keywords}.\n\n"
        f"صفحات PDF: {lesson.get('pdf_pages', [])}\n"
        f"صفحات الكتاب: {lesson.get('book_pages', [])}"
    )
    return RoutedAnswer(
        intent="lesson_navigation",
        answer=answer,
        confidence=1.0,
        page_numbers=list(lesson.get("pdf_pages", [])),
        suggested_next_action=f"يمكنك أن تسأل: لخص الدرس {lesson_no} أو اعطني أسئلة عليه.",
    )


def route_direct_answer(query: str) -> RoutedAnswer | None:
    """Return a deterministic answer for intents that should not start with vector search."""
    return _answer_water_equation(query) or _answer_formula(query) or _answer_lesson_navigation(query)
