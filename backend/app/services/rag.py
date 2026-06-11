"""Retrieval-Augmented Generation helpers."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from collections.abc import Callable

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis_client
from app.models.textbook import ContentSource, RagChunk
from app.services.chunking import extract_formula_terms, normalize_formula
from app.services.embeddings import embed_query
from app.services.rag_diagnostics import CandidateInfo, RetrievalDiagnostics
from app.services.safety_rules import ACID_TO_WATER_REWRITE

logger = logging.getLogger(__name__)

_CACHE: dict[str, tuple[float, list["RetrievedChunk"]]] = {}
_CACHE_TTL_SECONDS = 3600
_CACHE_VERSION = "v14"
# Allow local dry-run sources for retrieval/debugging without marking ingestion complete.
_RETRIEVABLE_SOURCE_STATUSES = [
    "completed",
    "completed_with_warnings",
    "dry_run_incomplete",
    "completed_text_only",
    "completed_with_image_fallback",
]
_POSTGRES_LEXICAL_TERM_LIMIT = 10

_ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u0621-\u064A]+", re.IGNORECASE)
_ARABIC_NORMALIZATION = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ؤ": "و",
        "ئ": "ي",
        "ى": "ي",
        "ة": "ه",
    }
)
_CHEMISTRY_GLYPH_NORMALIZATION = str.maketrans(
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
        "⁺": "+",
        "⁻": "-",
    }
)

# ---------------------------------------------------------------------------
# Stop-words removed from queries before retrieval
# ---------------------------------------------------------------------------
_QUERY_STOPWORDS = {
    # Instruction verbs
    "اشرح", "شرح", "فسر", "عرف", "تعريف", "وضح", "بين", "اذكر",
    "قولي", "تقولي", "قلي", "خبرني", "اخبرني", "ممكن", "يمكنك",
    "ساعدني", "اعطني", "اعطيني",
    # Question particles & pronouns
    "ما", "ماذا", "من", "في", "عن", "على", "الى", "الي",
    "هل", "كيف", "لماذا", "متى", "كم", "عند", "يحدث",
    "هو", "هي", "هذا", "هذه", "ذلك", "تلك",
    "لي", "لنا", "انا", "اريد", "بدي",
    # Book/subject references (noise for retrieval)
    "كتاب", "الكتاب", "كيمياء", "الكيمياء",
    "درس", "الدرس", "صفحه", "الصفحه",
    "سؤال", "السؤال", "جواب", "الجواب",
}

# ---------------------------------------------------------------------------
# Term expansion — maps a normalized root to related terms for recall boost
# ---------------------------------------------------------------------------
_TERM_EXPANSIONS = {
    "ماء": {"ماء", "الماء", "h2o", "h₂o", "مائي", "مائيه", "محلول", "المحلول"},
    "الماء": {"ماء", "الماء", "h2o", "h₂o", "مائي", "مائيه", "محلول", "المحلول"},
    "تفكك": {"تفكك", "التفكك", "يتفكك", "تتفكك", "تفاعلات التفكك", "تفكك الماء", "وعاء فولتا"},
    "تاين": {"تاين", "التاين", "يتاين", "تتاين", "كليا", "جزئيا", "ايونات"},
    "تركيز": {"تركيز", "التركيز", "مولاري", "مولي", "غرامي", "تمديد", "المحاليل"},
    "محلول": {"محلول", "المحلول", "محاليل", "المحاليل", "مذاب", "مذيب", "مائي"},
    "اسيتون": {"اسيتون", "الاسيتون", "المذيب العضوي", "مذيب عضوي", "طلاء الاظافر"},
    "طلاء": {"طلاء", "طلاء الاظافر", "اسيتون", "المذيب العضوي", "مذيب عضوي"},
    "كالسيوم": {
        "كالسيوم", "الكالسيوم", "اكسيد الكالسيوم", "أكسيد الكالسيوم",
        "هيدروكسيد الكالسيوم", "cao", "ca(oh)2", "ca(oh)₂",
    },
    "اكسيد": {"اكسيد", "أكسيد", "اكاسيد", "اوكسيد", "cao", "mgo", "co2"},
    "حموض": {
        "حموض", "الحموض", "حمض", "الحمض", "حمضي", "حمضيه", "الحمضيه",
        "احماض", "الاحماض",
        "هيدروجين", "الهيدروجين", "هدروجين", "الهدروجين", "هدرونيوم",
    },
    "حمض": {
        "حموض", "الحموض", "حمض", "الحمض", "حمضي", "حمضيه", "الحمضيه",
        "احماض", "الاحماض",
        "هيدروجين", "الهيدروجين", "هدروجين", "الهدروجين", "هدرونيوم",
    },
    "اسس": {
        "اسس", "الاسس", "اساس", "قاعده", "القاعده", "قواعد", "القواعد",
        "قلوي", "القلوي", "هيدروكسيد", "الهيدروكسيد",
        "ايونات الهدروكسيد", "ايون الهدروكسيد", "oh", "oh-",
        "مواد تعطي", "انحلالها", "المحاليل الاساسيه",
    },
    "قاعده": {
        "اسس", "الاسس", "قاعده", "القاعده", "قواعد", "القواعد",
        "قلوي", "القلوي", "هيدروكسيد", "الهيدروكسيد",
        "ايونات الهدروكسيد", "ايون الهدروكسيد", "oh", "oh-",
        "مواد تعطي", "انحلالها", "المحاليل الاساسيه",
    },
    "اساس": {
        "اسس", "الاسس", "اساس", "قاعده", "القاعده", "قواعد", "القواعد",
        "هيدروكسيد", "الهيدروكسيد", "ايونات الهدروكسيد", "oh-",
        "مواد تعطي", "انحلالها", "المحاليل الاساسيه",
    },
    "هيدروكسيد": {
        "هيدروكسيد", "الهيدروكسيد", "ايون الهدروكسيد", "ايونات الهدروكسيد",
        "oh", "oh-", "اسس", "الاسس", "قواعد", "القواعد",
    },
    "املاح": {
        "املاح", "الاملاح", "أملاح", "ملح", "الملح", "تعديل", "التعديل",
        "أيونات الملح", "ايونات الملح", "اسم الملح", "الصيغه الجزيئيه",
        "الصيغة الجزيئية", "يتشكل الملح", "يتشكّل الملح", "طرائق تحضير الاملاح",
        "كربونات الصوديوم", "كلوريد الصوديوم", "كبريتات الصوديوم",
    },
    "ملح": {
        "املاح", "الاملاح", "ملح", "الملح", "أيونات الملح", "ايونات الملح",
        "اسم الملح", "الصيغه الجزيئيه", "الصيغة الجزيئية", "يتشكل الملح",
        "يتشكّل الملح", "حمض مع اساس", "حمض مع معدن", "حمض مع ملح",
        "ملح مع ملح",
    },
    "صوديوم": {
        "صوديوم", "الصوديوم", "na", "na+", "كلوريد الصوديوم", "nacl",
        "كربونات الصوديوم", "na2co3", "كبريتات الصوديوم", "na2so4",
        "هيدروكسيد الصوديوم", "naoh",
    },
    "كربونات": {
        "كربونات", "الكربونات", "كربونات الصوديوم", "كربونات الكالسيوم",
        "na2co3", "caCO3", "caco3", "co3", "co32-", "co₃",
    },
    "تاكسد": {
        "تاكسد", "التاكسد", "اكسده", "الاكسده", "ارجاع", "الارجاع",
        "مؤكسد", "المؤكسد", "مرجع", "المرجع",
    },
    "ذره": {
        "ذره", "الذره", "ذرات", "الذرات", "نواه", "النواه",
        "الكترون", "الكترونات", "بروتون", "بروتونات", "نيوترون",
    },
    "ايون": {
        "ايون", "الايون", "ايونات", "الايونات", "شارده", "الشارده",
        "شوارد", "الشوارد", "تاين", "التاين",
    },
    "تفاعل": {
        "تفاعل", "التفاعل", "تفاعلات", "التفاعلات",
        "معادله", "المعادله", "ناتج", "النواتج", "متفاعل", "المتفاعلات",
        "ازاحه", "الازاحه", "احلال", "سلسله النشاط", "النشاط الكيميائي",
        "لا يحدث", "يزيح", "يزاح", "هيدروجين", "الهيدروجين",
    },
    "معادله": {
        "معادله", "المعادله", "تفاعل", "التفاعل", "تفاعلات",
        "موزونه", "وازن", "ناتج", "نواتج", "متفاعلات",
        "ازاحه", "احلال", "سلسله النشاط",
    },
    "نحاس": {
        "نحاس", "النحاس", "cu", "كبريتات النحاس", "اكسيد النحاس",
        "سلسله النشاط", "النشاط الكيميائي", "ازاحه", "احلال",
        "لا يحدث", "اقل نشاطا",
    },
    "حديد": {
        "حديد", "الحديد", "fe", "كبريتات الحديد", "كلوريد الحديد",
        "سلسله النشاط", "النشاط الكيميائي", "ازاحه", "احلال",
    },
    "زنك": {
        "زنك", "الزنك", "خارصين", "الخارصين", "zn",
        "حمض الكبريت", "حمض كلور الماء", "غاز الهدروجين", "هيدروجين",
    },
    "كبريت": {
        "كبريت", "الكبريت", "h2so4", "كبريتات",
    },
    "كبريتات": {"كبريتات", "كبريتات النحاس", "كبريتات الحديد", "كبريتات الزنك"},
    "ممدد": {
        "ممدد", "الممدد", "ممدده", "الممدده", "حمض الكبريت",
        "حمض كلور الماء", "غاز الهدروجين",
    },
    "اوكسجين": {
        "اوكسجين", "الاوكسجين", "أوكسجين", "الأوكسجين",
        "أكسجين", "الأكسجين", "اكسجين", "الاكسجين",
        "o2", "غاز الأكسجين", "غاز الاوكسجين", "الاحتراق",
    },
    "عضويه": {
        "عضويه", "العضويه", "الكيمياء العضويه", "الكربون", "مركبات الكربون",
        "مركبات عضويه", "هيدروكربونات",
    },
    "كربون": {"كربون", "الكربون", "مركبات الكربون", "الكيمياء العضويه", "روابط الكربون"},
    "اشعاعي": {"اشعاعي", "اشعاعيه", "النشاط الاشعاعي", "العناصر المشعه", "الفا", "بيتا", "غاما"},
    "أكسجين": {
        "اوكسجين", "الاوكسجين", "أوكسجين", "الأوكسجين",
        "أكسجين", "الأكسجين", "اكسجين", "الاكسجين",
        "o2", "غاز الأكسجين", "غاز الاوكسجين", "الاحتراق",
    },
}

# Content types that get a boost when the intent is definition_lookup
_DEFINITION_CONTENT_TYPES = {"definition", "summary", "concept", "key_point", "learned_summary", "result", "text"}
_OBJECTIVE_CONTENT_TYPES = {"objectives", "objective"}
_EQUATION_CONTENT_TYPES = {"equation", "activity", "result", "exercise", "mixed", "full_page"}
_EXERCISE_CONTENT_TYPES = {"exercise", "question", "questions", "exam_question"}
_INTENT_CONTENT_TYPE_BOOSTS = {
    "definition_lookup": {
        "definition": 0.24,
        "text": 0.10,
        "learned_summary": 0.16,
        "result": 0.14,
        "table": 0.04,
    },
    "formula_lookup": {
        "definition": 0.10,
        "equation": 0.18,
        "table": 0.12,
        "learned_summary": 0.08,
    },
    "equation_lookup": {
        "equation": 0.30,
        "result": 0.16,
        "learned_summary": 0.12,
        "exercise": 0.10,
        "table": 0.08,
    },
    "reaction_query": {
        "equation": 0.28,
        "result": 0.16,
        "exercise": 0.12,
        "table": 0.08,
    },
    "property_lookup": {
        "text": 0.08,
        "definition": 0.12,
        "result": 0.18,
        "learned_summary": 0.18,
        "table": 0.08,
    },
    "table_lookup": {
        "table": 0.28,
        "text": 0.08,
        "result": 0.06,
    },
    "exercise_lookup": {
        "exercise": 0.26,
        "equation": 0.18,
        "result": 0.12,
        "table": 0.10,
        "text": 0.04,
    },
    "exercise_solving": {
        "exercise": 0.28,
        "equation": 0.18,
        "result": 0.12,
        "table": 0.10,
        "text": 0.04,
    },
    "safety_question": {
        "warning": 0.34,
        "safety": 0.34,
        "objective": 0.12,
        "objectives": 0.12,
        "text": 0.10,
        "learned_summary": 0.08,
    },
    "book_grounded": {
        "definition": 0.12,
        "text": 0.10,
        "result": 0.10,
        "learned_summary": 0.10,
    },
}
_DEFINITION_PENALTY_MARKERS = (
    "الاهداف",
    "اﻫﺪاف",
    "يتعرف",
    "يتعرّف",
    "يميز",
    "يميّز",
    "احتياطات",
    "اثناء استعمال المحاليل",
    "أثناء استعمال المحاليل",
)

# ---------------------------------------------------------------------------
# Query cleanup & rewriting
# ---------------------------------------------------------------------------

# Phrases stripped entirely from the query before processing
_NOISE_PHRASES_RE = re.compile(
    r"(?:اشرح\s*لي|شرح\s*لي|وضح\s*لي|فسر\s*لي|عرف\s*لي|قول\s*لي|"
    r"ممكن\s*تقولي|ممكن\s*توضح|ممكن\s*تشرح|ممكن\s*تعطيني|"
    r"من\s*الكتاب|في\s*الكتاب|حسب\s*الكتاب|بحسب\s*الكتاب|"
    r"من\s*كتاب\s*الكيمياء|بالتفصيل|لو\s*سمحت|من\s*فضلك)",
    re.IGNORECASE,
)


def clean_query(raw_query: str) -> str:
    """Strip instruction-based noise and keep only content-bearing terms."""
    cleaned = _NOISE_PHRASES_RE.sub(" ", raw_query)
    cleaned = re.sub(r"[؟?!.،,؛;]+", " ", cleaned)
    cleaned = " ".join(cleaned.split()).strip()
    return cleaned or raw_query.strip()


def rewrite_query(cleaned_query: str) -> str:
    """Expand a cleaned query with semantically related terms for better recall."""
    normalized = _normalize_lexical_text(cleaned_query)
    if _acid_to_water_safety_query(normalized):
        return ACID_TO_WATER_REWRITE
    if "hcl" in normalized and "تركيز" in normalized and any(term in normalized for term in ("احسب", "مساله", "مسالة", "تمرين")):
        original = cleaned_query.strip()
        exercise_rewrite = (
            "مسألة تركيز حمض كلور الماء HCl التركيز الغرامي التركيز المولي "
            "Cm=m/V C=n/V كتلة حجم mol/L g/L"
        )
        return f"{original} {exercise_rewrite}".strip()

    terms = _query_terms(cleaned_query)
    original_tokens = [t for t in _tokens(cleaned_query) if t not in _QUERY_STOPWORDS and len(t) > 1]
    # Keep originals first, then add expansions
    all_parts = list(original_tokens)
    for term in terms:
        if term not in all_parts:
            all_parts.append(term)
    if any(term in normalized for term in ("تفاعل", "معادله", "معادلة")):
        for term in ("تفاعلات الازاحه", "سلسله النشاط", "النشاط الكيميائي", "لا يحدث تفاعل"):
            if term not in all_parts:
                all_parts.append(term)
    if any(term in normalized for term in ("اسس", "الاسس", "اساس", "قاعده", "قواعد")):
        for term in (
            "تعريف الاسس",
            "الاساس",
            "ايونات الهدروكسيد",
            "oh-",
            "المحاليل الاساسيه",
            "مواد تعطي",
            "عند انحلالها في الماء",
        ):
            if term not in all_parts:
                all_parts.append(term)
    if any(term in normalized for term in ("حموض", "احماض", "حمض")):
        for term in (
            "تعريف الحموض",
            "ايونات الهدروجين",
            "h+",
            "المحاليل الحمضيه",
            "مواد تعطي",
            "عند انحلالها في الماء",
        ):
            if term not in all_parts:
                all_parts.append(term)
    if "نحاس" in normalized and "حمض الكبريت" in normalized:
        for term in ("النحاس حمض الكبريت الممدد", "اقل نشاطا من الهيدروجين", "لا يحدث تفاعل"):
            if term not in all_parts:
                all_parts.append(term)
    return " ".join(all_parts)


@dataclass
class RetrievedChunk:
    """A retrieved textbook chunk with similarity metadata."""

    id: int
    source_id: int
    content: str
    source: str | None
    source_type: str
    content_type: str
    page_number: int | None
    chapter_id: int | None
    lesson_id: int | None
    topic_id: int | None
    metadata_json: dict | list | None
    similarity_score: float


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    pairs = zip(left, right)
    dot = sum(a * b for a, b in pairs)
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _embedding_values(embedding) -> list[float]:
    """Return pgvector/JSON embeddings as a plain list for Python scoring."""
    if embedding is None:
        return []
    if isinstance(embedding, list):
        return embedding
    if isinstance(embedding, tuple):
        return list(embedding)
    if hasattr(embedding, "tolist"):
        values = embedding.tolist()
        return values if isinstance(values, list) else list(values)
    return list(embedding)


def _normalize_lexical_text(text: str) -> str:
    """Normalize Arabic text enough for lexical matching over noisy OCR chunks."""
    lowered = text.lower().replace("ـ", "")
    lowered = lowered.translate(_CHEMISTRY_GLYPH_NORMALIZATION)
    without_diacritics = _ARABIC_DIACRITICS_RE.sub("", lowered)
    normalized = without_diacritics.translate(_ARABIC_NORMALIZATION)
    normalized = normalized.replace("اال", "ال")
    normalized = normalized.replace("السيتون", "الاسيتون")
    normalized = normalized.replace("طالء", "طلاء")
    normalized = normalized.replace("الظافر", "الاظافر")
    return normalized


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(_normalize_lexical_text(text))


def _query_terms(query: str) -> set[str]:
    terms: set[str] = set()
    for token in _tokens(query):
        if len(token) < 2 or token in _QUERY_STOPWORDS:
            continue
        terms.add(token)
        if token.startswith("ال") and len(token) > 4:
            terms.add(token[2:])
        if token.endswith("ات") and len(token) > 4:
            terms.add(token[:-2])
        if token.endswith("يه") and len(token) > 4:
            terms.add(token[:-1])

    expanded = set(terms)
    for term in terms:
        lookup_terms = {term}
        if term.startswith("ال") and len(term) > 4:
            lookup_terms.add(term[2:])
        for lookup in lookup_terms:
            expanded.update(_TERM_EXPANSIONS.get(lookup, set()))
    return expanded


def _matched_query_terms(query: str, content: str) -> list[str]:
    terms = _query_terms(query)
    normalized_content = _normalize_lexical_text(content)
    content_tokens = set(_tokens(content))
    matched = sorted(term for term in terms if term in content_tokens or term in normalized_content)
    return matched[:30]


def _formula_overlap(query: str, content: str) -> set[str]:
    query_formulas = {normalize_formula(item).lower() for item in extract_formula_terms(query)}
    content_formulas = {normalize_formula(item).lower() for item in extract_formula_terms(content)}
    return query_formulas & content_formulas


def _acid_to_water_safety_query(query_norm: str) -> bool:
    return (
        "حمض" in query_norm
        and "ماء" in query_norm
        and any(
            term in query_norm
            for term in (
                "نضيف",
                "اضف",
                "اضافه",
                "اضافة",
                "العكس",
                "وليس",
                "احتياطات",
                "السلامه",
                "السلامة",
            )
        )
    )


def _acid_to_water_safety_content(normalized_content: str) -> bool:
    return (
        "حمض" in normalized_content
        and "ماء" in normalized_content
        and any(
            term in normalized_content
            for term in (
                "اضف الحمض الى الماء",
                "اضافه الحمض الى الماء",
                "تحذير",
                "احتياطات",
                "السلامه",
                "السلامة",
                "تطاير",
                "غليان",
            )
        )
    )


def _candidate_reasons(query: str, content: str, *, intent: str, content_type: str) -> list[str]:
    reasons: list[str] = []
    matched = _matched_query_terms(query, content)
    normalized = _normalize_lexical_text(content)
    query_norm = _normalize_lexical_text(query)
    if matched:
        reasons.append(f"matched_terms:{','.join(matched[:8])}")
    if content_type in _INTENT_CONTENT_TYPE_BOOSTS.get(intent, {}):
        reasons.append(f"intent_content_type_boost:{intent}:{content_type}")
    formulas = _formula_overlap(query, content)
    if formulas:
        reasons.append(f"exact_formula:{','.join(sorted(formulas))}")
    if "عباد الشمس" in query_norm and "عباد الشمس" in normalized:
        reasons.append("exact_entity:litmus")
    if "اكسيد الكالسيوم" in query_norm and (
        "اكسيد الكالسيوم" in normalized or "هيدروكسيد الكالسيوم" in normalized or "cao" in normalized
    ):
        reasons.append("exact_entity:calcium_oxide")
    if "كربونات الصوديوم" in query_norm and ("كربونات الصوديوم" in normalized or "na2co3" in normalized):
        reasons.append("exact_entity:sodium_carbonate")
    if _acid_to_water_safety_query(query_norm) and _acid_to_water_safety_content(normalized):
        reasons.append("acid_to_water_safety_warning")
    if any(term in query_norm for term in ("املاح", "الاملاح", "ملح", "الملح")) and any(
        term in normalized for term in ("ايونات الملح", "اسم الملح", "يتشكل الملح", "يتشكل الملح")
    ):
        reasons.append("salt_concept_evidence")
    return reasons[:8]


def lexical_relevance_score(query: str, content: str) -> float:
    """Return a 0..1 Arabic lexical relevance score for a query/content pair."""
    terms = _query_terms(query)
    if not terms:
        return 0.0

    normalized_content = _normalize_lexical_text(content)
    content_tokens = set(_tokens(content))
    exact_hits = sum(1 for term in terms if term in content_tokens)
    substring_hits = sum(1 for term in terms if term not in content_tokens and term in normalized_content)
    if exact_hits == 0 and substring_hits == 0:
        return 0.0

    original_terms = [token for token in _tokens(query) if token not in _QUERY_STOPWORDS and len(token) > 2]
    original_hits = sum(1 for term in original_terms if term in content_tokens or term in normalized_content)
    original_ratio = original_hits / max(len(original_terms), 1)

    score = min(0.72, (exact_hits * 0.12) + (substring_hits * 0.06))
    score += min(0.2, original_ratio * 0.2)

    focus_terms = {term for term in original_terms if len(term) > 3}
    if any(f":{term}" in normalized_content or f"{term}:" in normalized_content for term in focus_terms):
        score += 0.12
    if any(term in {"حموض", "حمض", "احماض"} for term in terms) and (
        "ايون الهدروجين" in normalized_content
        or "ايونات الهدروجين" in normalized_content
        or "h+" in normalized_content
    ):
        score += 0.16
    if any(term in {"اسس", "اساس", "قاعده", "قواعد"} for term in terms) and (
        "ايون الهدروكسيد" in normalized_content
        or "ايونات الهدروكسيد" in normalized_content
        or "oh-" in normalized_content
        or "oh⁻" in normalized_content
    ):
        score += 0.22

    return round(min(score, 1.0), 4)


def _hybrid_score(
    query: str,
    content: str,
    vector_score: float,
    *,
    intent: str = "general",
    content_type: str = "text",
    source_type: str = "textbook",
) -> float:
    """Compute a blended vector+lexical score with intent-based boosting."""
    lexical_score = lexical_relevance_score(query, content)
    if lexical_score <= 0:
        score = max(vector_score, 0.0) * 0.72
    else:
        blended = (0.55 * max(vector_score, 0.0)) + (0.45 * lexical_score)
        score = max(blended, lexical_score, vector_score)
    # Exact lexical matches in the textbook should outrank weak local/hash embeddings.

    normalized = _normalize_lexical_text(content)
    query_norm = _normalize_lexical_text(query)
    base_query = any(term in query_norm for term in ("اسس", "اساس", "قاعده", "قواعد", "اساسي", "اساسيه"))
    acid_query = any(term in query_norm for term in ("حموض", "احماض", "حمض", "حمضي", "حمضيه"))
    salt_query = any(term in query_norm for term in ("املاح", "الاملاح", "ملح", "الملح"))
    sodium_carbonate_query = "كربونات الصوديوم" in query_norm or "na2co3" in query_norm
    base_markers = ("هيدروكسيد", "oh-", "oh⁻", "oh", "الاسس", "اساس", "اساسيه", "قلوي")
    acid_markers = ("حموض", "حمض", "حمضيه", "هيدروجين", "هدروجين", "h+", "h⁺")

    # Content-type boost for definition-oriented intents
    if intent == "definition_lookup":
        if content_type in _DEFINITION_CONTENT_TYPES:
            score += 0.18
        if content_type in _OBJECTIVE_CONTENT_TYPES:
            score -= 0.32
        if content_type in _EXERCISE_CONTENT_TYPES:
            score -= 0.22
        elif any(marker in normalized for marker in _DEFINITION_PENALTY_MARKERS):
            score -= 0.08
        if "مواد تعطي" in normalized:
            score += 0.16
        if "عند انحلالها في الماء" in normalized or "انحلالها في الماء" in normalized:
            score += 0.14
        if base_query:
            if "ايونات الهدروكسيد" in normalized or "ايون الهدروكسيد" in normalized or "oh-" in normalized:
                score += 0.28
            if "المحاليل الاساسيه" in normalized:
                score += 0.10
        if acid_query:
            if "ايونات الهدروجين" in normalized or "ايون الهدروجين" in normalized or "h+" in normalized:
                score += 0.24
        if salt_query:
            if any(marker in normalized for marker in ("ايونات الملح", "اسم الملح", "الصيغه الجزيئيه")):
                score += 0.24
            if "يتشكل الملح" in normalized or "يتشكّل الملح" in normalized:
                score += 0.18
    elif intent in {"equation_lookup", "reaction_query"}:
        if content_type in _EQUATION_CONTENT_TYPES:
            score += 0.18
        if content_type in _DEFINITION_CONTENT_TYPES:
            score -= 0.10
        if "نحاس" in query_norm and "حمض الكبريت" in query_norm:
            if "النحاس مع حمض الكبريت" in normalized:
                score += 0.30
            if "سلسله النشاط" in normalized or "تفاعلات الازاحه" in normalized:
                score += 0.18
            if "لا يحدث" in normalized:
                score += 0.22

    score += _INTENT_CONTENT_TYPE_BOOSTS.get(intent, {}).get(content_type, 0.0)

    # Entity match boost for chemical formula presence
    formula_overlap = _formula_overlap(query, content)
    if formula_overlap:
        score += min(0.24, 0.08 * len(formula_overlap))
    if "عباد الشمس" in query_norm and "عباد الشمس" in normalized:
        score += 0.20
    if _acid_to_water_safety_query(query_norm):
        if _acid_to_water_safety_content(normalized):
            score += 0.58
        elif content_type in {"definition", "result", "learned_summary"} and (
            "ايونات الهدروجين" in normalized
            or "ايون الهدروجين" in normalized
            or "ايونات الهيدروجين" in normalized
            or "ايون الهيدروجين" in normalized
            or "h+" in normalized
            or "مواد تعطي" in normalized
            or "تتاين الحموض" in normalized
        ):
            score = min(score, 0.32)
    if "اكسيد الكالسيوم" in query_norm and (
        "اكسيد الكالسيوم" in normalized or "هيدروكسيد الكالسيوم" in normalized or "cao" in normalized
    ):
        score += 0.28
    if sodium_carbonate_query:
        if "كربونات الصوديوم" in normalized or "na2co3" in normalized or "na co3" in normalized:
            score += 0.34
        else:
            score -= 0.34
    if salt_query and any(marker in normalized for marker in ("ايونات الملح", "اسم الملح", "يتشكل الملح", "يتشكّل الملح")):
        score += 0.16
    if "تفكك الماء" in query_norm and ("وعاء فولتا" in normalized or "h2o" in normalized):
        score += 0.20

    if base_query:
        if not any(marker in normalized for marker in base_markers):
            score -= 0.42
        if any(marker in normalized for marker in acid_markers) and not any(marker in normalized for marker in base_markers):
            score -= 0.30
        if "عباد الشمس" in query_norm and ("حمضيه" in normalized or "الاحمر" in normalized):
            score -= 0.45
    if acid_query and not base_query:
        if any(marker in normalized for marker in base_markers) and not any(marker in normalized for marker in acid_markers):
            score -= 0.30
    if "اشعاعي" in query_norm and "اشعاعي" not in normalized and "مشعه" not in normalized:
        score -= 0.50
    if "اسيتون" in query_norm and "اسيتون" not in normalized:
        score -= 0.50
    if "طلاء الاظافر" in query_norm and "طلاء الاظافر" not in normalized:
        score -= 0.25

    # Solution book boost: for exercise_solving intent, prefer solution_book chunks
    # and boost exact formula / calculation content within them.
    if intent == "exercise_solving" and source_type in {"solution_book", "solutions"}:
        score += 0.22
        if content_type in {"exercise_solution", "solution_step", "final_answer", "equation"}:
            score += 0.14
        # Boost if query contains numeric values that also appear in content
        query_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", query))
        content_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", content))
        if query_numbers & content_numbers:
            score += 0.10

    return round(min(max(score, 0.0), 1.0), 4)


def _retrieved_from_chunk(chunk: RagChunk, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        id=chunk.id,
        source_id=chunk.source_id,
        content=chunk.content,
        source=chunk.source.title if chunk.source else None,
        source_type=chunk.source_type,
        content_type=chunk.content_type,
        page_number=chunk.page_number,
        chapter_id=chunk.chapter_id,
        lesson_id=chunk.lesson_id,
        topic_id=chunk.topic_id,
        metadata_json=chunk.metadata_json,
        similarity_score=score,
    )


async def retrieve_context(
    db: AsyncSession,
    query: str,
    user_id: int | None = None,
    chapter_id: int | None = None,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    source_types: list[str] | None = None,
    content_types: list[str] | None = None,
    top_k: int = 6,
    min_similarity: float = 0.0,
    intent: str = "general",
    diagnostics_callback: Callable[[dict], None] | None = None,
    # Solution book extended filters
    document_type: str | None = None,
    document_id: str | None = None,
    related_document_id: str | None = None,
    lesson_no: int | None = None,
    source_pdf: str | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
) -> list[RetrievedChunk]:
    """Retrieve relevant source chunks for a query.

    Uses PostgreSQL pgvector if available, otherwise falls back to Python-based
    cosine similarity for SQLite local development. Uses Redis for caching.
    """
    diag = RetrievalDiagnostics()
    diag.original_query = query
    diag.detected_intent = intent
    diag.start_timer()

    # --- Query cleanup & rewriting ---
    cleaned = clean_query(query)
    diag.normalized_query = cleaned
    rewritten = rewrite_query(cleaned)
    diag.rewritten_query = rewritten
    terms = _query_terms(cleaned)
    diag.query_terms = sorted(terms)

    cache_key_raw = (
        f"{query}|{user_id}|{chapter_id}|{lesson_id}|{topic_id}|"
        f"{source_types}|{content_types}|{top_k}|{min_similarity}|{intent}|"
        f"{document_type}|{document_id}|{lesson_no}|{page_start}|{page_end}"
    )
    cache_key = f"rag_cache:{_CACHE_VERSION}:" + hashlib.md5(cache_key_raw.encode()).hexdigest()

    redis = get_redis_client()
    try:
        cached = await redis.get(cache_key)
        if cached:
            chunks_dict = json.loads(cached)
            diag.cache_hit = True
            diag.final_confidence = max((c.get("similarity_score", 0) for c in chunks_dict), default=0)
            if diagnostics_callback:
                diagnostics_callback(diag.as_payload())
            diag.emit()
            return [RetrievedChunk(**c) for c in chunks_dict]
    except Exception:
        pass
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass

    # Use the rewritten query for embeddings, but the cleaned user query for
    # lexical reranking so expansion terms do not overpower exact entities.
    retrieval_query = rewritten or cleaned
    scoring_query = cleaned or query
    query_embedding = await embed_query(retrieval_query)

    stmt = (
        select(RagChunk)
        .options(selectinload(RagChunk.source))
        .join(RagChunk.source)
        .where(
            RagChunk.embedding.isnot(None),
            ContentSource.status.in_(_RETRIEVABLE_SOURCE_STATUSES),
        )
    )

    if chapter_id is not None:
        stmt = stmt.where(RagChunk.chapter_id == chapter_id)
    if lesson_id is not None:
        stmt = stmt.where(RagChunk.lesson_id == lesson_id)
    if topic_id is not None:
        stmt = stmt.where(RagChunk.topic_id == topic_id)
    if source_types:
        stmt = stmt.where(RagChunk.source_type.in_(source_types))
    if content_types:
        stmt = stmt.where(RagChunk.content_type.in_(content_types))
    if page_start is not None:
        stmt = stmt.where(RagChunk.page_number >= page_start)
    if page_end is not None:
        stmt = stmt.where(RagChunk.page_number <= page_end)
    # Solution book extended SQL filters (stored in source_type column for index performance)
    if document_type is not None and not source_types:
        stmt = stmt.where(RagChunk.source_type == document_type)

    scored: list[RetrievedChunk] = []
    all_candidates: list[CandidateInfo] = []

    # Check if we are running on PostgreSQL
    is_postgres = db.bind.dialect.name == "postgresql" if db.bind else False

    if is_postgres:
        # pgvector SQL path (cosine distance)
        # Pull extra candidates, then rerank with lexical matches to handle Arabic OCR text.
        candidate_limit = max(top_k * 12, 48)
        vector_stmt = stmt.order_by(RagChunk.embedding.cosine_distance(query_embedding)).limit(candidate_limit)
        result = await db.execute(vector_stmt)
        chunks_by_id = {chunk.id: chunk for chunk in result.scalars().all()}

        lexical_terms = sorted(
            {term for term in terms if len(term) > 1},
            key=lambda value: (not bool(re.search(r"[a-z0-9]", value)), -len(value), value),
        )[:_POSTGRES_LEXICAL_TERM_LIMIT]
        lexical_filters = []
        for term in lexical_terms:
            pattern = f"%{term}%"
            lexical_filters.append(RagChunk.content.ilike(pattern))
            lexical_filters.append(RagChunk.normalized_content.ilike(pattern))
        if lexical_filters:
            lexical_stmt = stmt.where(or_(*lexical_filters)).limit(candidate_limit)
            result = await db.execute(lexical_stmt)
            for chunk in result.scalars().all():
                chunks_by_id.setdefault(chunk.id, chunk)

        chunks_list = list(chunks_by_id.values())
    else:
        # SQLite Python fallback path — load all and score in Python
        result = await db.execute(stmt)
        chunks_list = list(result.scalars().all())

    diag.total_candidates_scanned = len(chunks_list)

    for chunk in chunks_list:
        vector_score = _cosine_similarity(query_embedding, _embedding_values(chunk.embedding))
        # Use both original content and normalized content for lexical matching
        lexical_content = f"{chunk.normalized_content or ''}\n{chunk.content}"
        lex_score = lexical_relevance_score(scoring_query, lexical_content)
        score = _hybrid_score(
            scoring_query, lexical_content, vector_score,
            intent=intent, content_type=chunk.content_type,
            source_type=chunk.source_type,
        )

        # Track all candidates for diagnostics
        candidate = CandidateInfo(
            chunk_id=chunk.id,
            page_number=chunk.page_number,
            source_type=chunk.source_type,
            content_type=chunk.content_type,
            vector_score=round(vector_score, 4),
            lexical_score=round(lex_score, 4),
            hybrid_score=round(score, 4),
            snippet=chunk.content[:120].replace("\n", " "),
            matched_terms=_matched_query_terms(scoring_query, lexical_content),
            reasons=_candidate_reasons(
                scoring_query,
                lexical_content,
                intent=intent,
                content_type=chunk.content_type,
            ),
        )
        all_candidates.append(candidate)

        if score >= min_similarity:
            scored.append(_retrieved_from_chunk(chunk, score))

    scored.sort(key=lambda item: item.similarity_score, reverse=True)
    scored = scored[:top_k]

    # --- Diagnostics ---
    all_candidates.sort(key=lambda c: c.hybrid_score, reverse=True)
    diag.top_candidates = all_candidates[:10]
    diag.final_top_k = [
        CandidateInfo(
            chunk_id=s.id,
            page_number=s.page_number,
            source_type=s.source_type,
            content_type=s.content_type,
            vector_score=0.0,  # not stored in RetrievedChunk
            lexical_score=0.0,
            hybrid_score=s.similarity_score,
            snippet=s.content[:120].replace("\n", " "),
            matched_terms=_matched_query_terms(scoring_query, s.content),
            reasons=_candidate_reasons(
                scoring_query,
                s.content,
                intent=intent,
                content_type=s.content_type,
            ),
        )
        for s in scored
    ]
    diag.final_confidence = max((s.similarity_score for s in scored), default=0.0)
    if diagnostics_callback:
        diagnostics_callback(diag.as_payload())
    diag.emit()

    # --- Cache ---
    redis = get_redis_client()
    try:
        data_to_cache = [c.__dict__ for c in scored]
        await redis.setex(cache_key, _CACHE_TTL_SECONDS, json.dumps(data_to_cache))
    except Exception:
        pass
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass

    return scored


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks for insertion into an AI system prompt."""
    parts = []
    for chunk in chunks:
        ref = f"صفحة {chunk.page_number}" if chunk.page_number else chunk.source or "الكتاب"
        parts.append(f"{chunk.content}\n[المصدر: {ref}, النوع: {chunk.source_type}/{chunk.content_type}]")
    return "\n\n---\n\n".join(parts)
