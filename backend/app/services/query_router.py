"""Deterministic routing for short Arabic chemistry questions before generic RAG."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from app.core.config import PROJECT_DIR
from app.services.chemistry_rules import answer_metal_dilute_acid_reaction

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
    route: str = "dictionary_first"
    grounding: str = "approved_dictionary"
    extracted_values: dict | None = None


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
    {
        "entity": "ثاني أكسيد الكربون",
        "aliases": ["ثاني أكسيد الكربون", "ثاني اكسيد الكربون", "co2", "co₂"],
        "formula": "CO₂",
        "formula_ascii": "CO2",
        "pages": [79],
        "kind": "formula",
    },
    {
        "entity": "أحادي أكسيد الكربون",
        "aliases": ["أحادي أكسيد الكربون", "احادي اكسيد الكربون", "أول أكسيد الكربون", "اول اكسيد الكربون", "co"],
        "formula": "CO",
        "formula_ascii": "CO",
        "pages": [],
        "kind": "formula",
    },
    {
        "entity": "كربونات الكالسيوم",
        "aliases": ["كربونات الكالسيوم", "caco3", "caco₃"],
        "formula": "CaCO₃",
        "formula_ascii": "CaCO3",
        "pages": [43],
        "kind": "formula",
    },
    {
        "entity": "ثاني أكسيد الكبريت",
        "aliases": ["ثاني أكسيد الكبريت", "ثاني اكسيد الكبريت", "so2", "so₂"],
        "formula": "SO₂",
        "formula_ascii": "SO2",
        "pages": [],
        "kind": "formula",
    },
    {
        "entity": "النشادر",
        "aliases": ["النشادر", "الأمونيا", "الامونيا", "nh3", "nh₃"],
        "formula": "NH₃",
        "formula_ascii": "NH3",
        "pages": [],
        "kind": "formula",
    },
    {
        "entity": "الميثان",
        "aliases": ["الميثان", "ميثان", "ch4", "ch₄"],
        "formula": "CH₄",
        "formula_ascii": "CH4",
        "pages": [],
        "kind": "formula",
    },
    {
        "entity": "الحديد",
        "aliases": ["الحديد", "حديد", "fe"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Fe",
        "pages": [43, 45],
        "kind": "element",
    },
    {
        "entity": "النحاس",
        "aliases": ["النحاس", "نحاس", "cu"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Cu",
        "pages": [43, 45],
        "kind": "element",
    },
    {
        "entity": "الزنك",
        "aliases": ["الزنك", "زنك", "zn"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Zn",
        "pages": [43, 45],
        "kind": "element",
    },
    {
        "entity": "المغنزيوم",
        "aliases": ["المغنزيوم", "مغنزيوم", "المغنيسيوم", "mg"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Mg",
        "pages": [43, 45],
        "kind": "element",
    },
    {
        "entity": "الألمنيوم",
        "aliases": ["الألمنيوم", "الالمنيوم", "المنيوم", "al"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Al",
        "pages": [43, 45],
        "kind": "element",
    },
    {
        "entity": "الفضة",
        "aliases": ["الفضة", "فضة", "ag"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Ag",
        "pages": [43, 45],
        "kind": "element",
    },
    {
        "entity": "الذهب",
        "aliases": ["الذهب", "ذهب", "au"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Au",
        "pages": [],
        "kind": "element",
    },
    {
        "entity": "الكالسيوم",
        "aliases": ["الكالسيوم", "كالسيوم", "ca"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Ca",
        "pages": [],
        "kind": "element",
    },
    {
        "entity": "الصوديوم",
        "aliases": ["الصوديوم", "صوديوم", "na"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Na",
        "pages": [],
        "kind": "element",
    },
    {
        "entity": "البوتاسيوم",
        "aliases": ["البوتاسيوم", "بوتاسيوم", "k"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "K",
        "pages": [],
        "kind": "element",
    },
    {
        "entity": "الكربون",
        "aliases": ["الكربون", "كربون", "c"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "C",
        "pages": [60, 63],
        "kind": "element",
    },
    {
        "entity": "الآزوت",
        "aliases": ["الآزوت", "الازوت", "النيتروجين", "نيتروجين", "n"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "N",
        "pages": [],
        "kind": "element",
    },
    {
        "entity": "الكبريت",
        "aliases": ["الكبريت", "كبريت", "s"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "S",
        "pages": [9, 11],
        "kind": "element",
    },
    {
        "entity": "الكلور",
        "aliases": ["الكلور", "كلور", "cl"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Cl",
        "pages": [5, 11, 17],
        "kind": "element",
    },
    {
        "entity": "الرصاص",
        "aliases": ["الرصاص", "رصاص", "pb"],
        "formula": None,
        "formula_ascii": None,
        "symbol": "Pb",
        "pages": [],
        "kind": "element",
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
    candidates: list[tuple[int, int, dict]] = []
    for index, fact in enumerate(_CHEMISTRY_FACTS):
        for alias in fact["aliases"]:
            normalized_alias = normalize_query(alias)
            if not normalized_alias:
                continue
            if re.fullmatch(r"[a-z0-9]+", normalized_alias):
                pattern = rf"(?<![a-z0-9]){re.escape(normalized_alias)}(?![a-z0-9])"
                matched = re.search(pattern, normalized) is not None
            else:
                matched = normalized_alias in normalized
            if matched:
                candidates.append((len(normalized_alias), -index, fact))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def _answer_formula(query: str) -> RoutedAnswer | None:
    normalized = normalize_query(query)
    if not _contains_any(normalized, ("رمز", "صيغه", "الصيغه", "formula", "فورمولا")):
        return None
    fact = _find_fact(query)
    if not fact:
        return None
    kind = fact.get("kind", "formula")
    if kind == "element":
        symbol = fact.get("symbol", "")
        answer = f"رمز عنصر {fact['entity']} هو: {symbol}."
        return RoutedAnswer(
            intent="formula_lookup",
            answer=answer,
            confidence=1.0,
            page_numbers=list(fact["pages"]),
            suggested_next_action="يمكنك أن تسأل عن خصائص هذا العنصر أو موقعه في سلسلة النشاط.",
        )
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


def _format_number(value: float) -> str:
    text = f"{value:.6g}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _extract_numeric_before_unit(normalized: str, units: tuple[str, ...]) -> float | None:
    unit_pattern = "|".join(re.escape(unit) for unit in units)
    match = re.search(rf"(\d+(?:\.\d+)?)\s*(?:{unit_pattern})", normalized)
    if not match:
        return None
    return float(match.group(1))


def _answer_hcl_concentration_exercise(query: str) -> RoutedAnswer | None:
    """Backward-compatible entry point — delegates to the generalized solver."""
    return _answer_concentration_exercise(query)


# Known compound formulas and their molar masses.
# Loaded lazily from chemistry_entities.json and augmented with hardcoded
# fallbacks so the math solver never silently fails.
_MOLAR_MASS_CACHE: dict[str, tuple[str, float, str]] | None = None


def _load_molar_mass_table() -> dict[str, tuple[str, float, str]]:
    """Return {normalized_formula: (display_formula, molar_mass, name_ar)}."""
    global _MOLAR_MASS_CACHE
    if _MOLAR_MASS_CACHE is not None:
        return _MOLAR_MASS_CACHE

    table: dict[str, tuple[str, float, str]] = {
        "hcl": ("HCl", 36.5, "حمض كلور الماء"),
        "naoh": ("NaOH", 40.0, "هيدروكسيد الصوديوم"),
        "h2so4": ("H₂SO₄", 98.0, "حمض الكبريت"),
        "nacl": ("NaCl", 58.5, "كلوريد الصوديوم"),
    }

    try:
        import json
        from app.core.config import BACKEND_DIR
        path = BACKEND_DIR / "app" / "rag" / "data" / "chemistry_entities.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        for item in raw:
            mm = item.get("molar_mass_g_mol")
            formula = item.get("formula")
            if mm and formula:
                key = normalize_query(formula)
                if key not in table:
                    table[key] = (formula, float(mm), item.get("entity_ar", formula))
    except Exception:
        pass  # Fallback to hardcoded table

    _MOLAR_MASS_CACHE = table
    return table


def _detect_compound_in_query(normalized: str) -> tuple[str, float, str] | None:
    """Return (display_formula, molar_mass, name_ar) for the first recognized compound."""
    table = _load_molar_mass_table()
    # Check longest keys first to avoid partial matches
    for key in sorted(table, key=len, reverse=True):
        if key in normalized:
            return table[key]
    return None


_EXERCISE_TRIGGERS = ("احسب", "حل", "مساله", "تمرين", "اوجد", "جد", "ايجاد")


def _answer_concentration_exercise(query: str) -> RoutedAnswer | None:
    """Solve Grade 9 concentration problems for any compound with known molar mass."""
    normalized = normalize_query(query)

    # Must mention concentration and a calculation trigger
    if "تركيز" not in normalized:
        return None
    if not _contains_any(normalized, _EXERCISE_TRIGGERS):
        return None

    compound = _detect_compound_in_query(normalized)
    if compound is None:
        return None
    display_formula, molar_mass, name_ar = compound

    mass_g = _extract_numeric_before_unit(normalized, ("g", "غ", "غرام", "غراما", "غراماً"))
    volume_ml = _extract_numeric_before_unit(normalized, ("ml", "مل", "ميلي", "ميليلتر", "ميلي لتر"))
    if mass_g is None or volume_ml is None or volume_ml <= 0:
        return None

    volume_l = volume_ml / 1000
    mass_text = _format_number(mass_g)
    volume_l_text = _format_number(volume_l)
    molar_mass_text = _format_number(molar_mass)
    cm = mass_g / volume_l
    moles = mass_g / molar_mass
    molarity = moles / volume_l
    cm_text = _format_number(cm)
    moles_text = _format_number(moles)
    molarity_text = _format_number(molarity)

    answer = (
        "نحل المسألة مباشرة من القيم المعطاة:\n\n"
        f"المعطيات: m = {mass_text} g، V = {volume_l_text} L، M({display_formula}) = {molar_mass_text} g/mol.\n\n"
        f"Cm = m / V = {mass_text} / {volume_l_text} = {cm_text} g/L\n"
        f"n = m / M = {mass_text} / {molar_mass_text} = {moles_text} mol\n"
        f"C = n / V = {moles_text} / {volume_l_text} = {molarity_text} mol/L\n\n"
        f"إذن التركيز الغرامي = {cm_text} g/L، والتركيز المولي = {molarity_text} mol/L."
    )
    return RoutedAnswer(
        intent="exercise_solving",
        answer=answer,
        confidence=1.0,
        page_numbers=[4, 7],
        suggested_next_action="يمكنك أن ترسل مسألة تركيز أخرى مع الكتلة والحجم.",
        route="math_solver",
        grounding="math_solver",
        extracted_values={
            "compound": display_formula,
            "mass_g": mass_g,
            "volume_ml": volume_ml,
            "volume_l": volume_l,
            "molar_mass_g_mol": molar_mass,
            "Cm_g_L": round(cm, 4),
            "n_mol": round(moles, 4),
            "C_mol_L": round(molarity, 4),
        },
    )


def _answer_molar_concentration_definition(query: str) -> RoutedAnswer | None:
    normalized = normalize_query(query)
    if not ("تركيز" in normalized and ("مولي" in normalized or "موليه" in normalized)):
        return None
    if not _contains_any(normalized, ("ما هو", "ماهي", "ما هي", "تعريف", "عرف", "قانون")):
        return None
    answer = (
        "التركيز المولي هو عدد مولات المادة المذابة في ليتر واحد من المحلول.\n\n"
        "القانون:\n"
        "C = n / V\n\n"
        "حيث C هو التركيز المولي، و n عدد المولات، و V حجم المحلول بالليتر. "
        "واحدته mol/L."
    )
    return RoutedAnswer(
        intent="definition_lookup",
        answer=answer,
        confidence=0.96,
        page_numbers=[4, 7],
        suggested_next_action="يمكنك أن تسألني عن مثال حسابي للتركيز المولي.",
        route="dictionary_first",
        grounding="approved_dictionary",
    )


def _book_structure_path(source_slug: str = "syria_grade_9_chemistry") -> Path:
    return PROJECT_DIR / "data" / "textbooks" / source_slug / "book_structure.json"


def _book_structure_candidates(source_slug: str = "syria_grade_9_chemistry") -> list[Path]:
    repo_root = Path(__file__).resolve().parents[4]
    return [
        repo_root / "src" / "data" / "textbooks" / source_slug / "book_structure.json",
        repo_root / "data" / "processed" / "book_structure.json",
        _book_structure_path(source_slug),
    ]


def _lesson_range(values: list | tuple | None, start: int | None, end: int | None) -> list[int]:
    if isinstance(values, (list, tuple)) and values:
        return [int(item) for item in values if isinstance(item, int)]
    if isinstance(start, int) and isinstance(end, int):
        return [start, end]
    if isinstance(start, int):
        return [start]
    return []


def _lesson_keywords(lesson: dict) -> list[str]:
    if isinstance(lesson.get("keywords"), list):
        return [str(item) for item in lesson["keywords"] if str(item).strip()]
    topics = lesson.get("topics") or []
    if isinstance(topics, list):
        return [
            str(item.get("title_ar") or item.get("title") or item.get("subtopic_title"))
            for item in topics
            if isinstance(item, dict) and str(item.get("title_ar") or item.get("title") or item.get("subtopic_title") or "").strip()
        ]
    return []


def _normalize_book_structure(payload: dict) -> dict:
    if isinstance(payload.get("lessons"), list):
        return payload

    lessons: list[dict] = []
    for unit in payload.get("units") or []:
        unit_lessons = list(unit.get("lessons") or [])
        for chapter in unit.get("chapters") or []:
            unit_lessons.extend(chapter.get("lessons") or [])
        for lesson in unit_lessons:
            if not isinstance(lesson, dict):
                continue
            lesson_no = lesson.get("lesson_no") or lesson.get("lesson_number")
            try:
                lesson_no = int(lesson_no)
            except (TypeError, ValueError):
                continue
            lessons.append(
                {
                    "lesson_no": lesson_no,
                    "title": lesson.get("title_ar") or lesson.get("lesson_title") or lesson.get("title") or f"الدرس {lesson_no}",
                    "objectives": lesson.get("objectives") or [],
                    "keywords": _lesson_keywords(lesson),
                    "pdf_pages": _lesson_range(
                        lesson.get("pdf_pages"),
                        lesson.get("pdf_page_start"),
                        lesson.get("pdf_page_end"),
                    ),
                    "book_pages": _lesson_range(
                        lesson.get("book_pages"),
                        lesson.get("printed_page_start"),
                        lesson.get("printed_page_end"),
                    ),
                }
            )
    return {**payload, "lessons": lessons}


def load_book_structure(source_slug: str = "syria_grade_9_chemistry") -> dict:
    for path in _book_structure_candidates(source_slug):
        if path.exists():
            return _normalize_book_structure(json.loads(path.read_text(encoding="utf-8")))
    return {"lessons": []}



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
    reaction = answer_metal_dilute_acid_reaction(query)
    if reaction:
        return RoutedAnswer(
            intent=reaction.intent,
            answer=reaction.answer,
            confidence=reaction.confidence,
            page_numbers=reaction.page_numbers,
            suggested_next_action=reaction.suggested_next_action,
            route="chemistry_rule",
            grounding="book_knowledge",
        )
    return (
        _answer_hcl_concentration_exercise(query)
        or _answer_molar_concentration_definition(query)
        or _answer_water_equation(query)
        or _answer_formula(query)
        or _answer_lesson_navigation(query)
    )
