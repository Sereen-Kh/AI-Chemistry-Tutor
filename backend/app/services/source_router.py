"""Source routing for textbook vs. solutions retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re

from app.core.redis import get_redis_client

ROUTE_TEXTBOOK = "textbook"
ROUTE_SOLUTIONS = "solution_book"
ROUTE_BOTH = "both"
# Legacy alias so that any existing DB rows with source_type="solutions" still match
_LEGACY_SOLUTIONS_ALIAS = "solutions"
ROUTABLE_SOURCE_TYPES = {ROUTE_TEXTBOOK, ROUTE_SOLUTIONS, _LEGACY_SOLUTIONS_ALIAS}
_CACHE_TTL_SECONDS = 600
_CACHE_VERSION = "v1"

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
_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")

_SOLUTIONS_PATTERNS = (
    "احسب",
    "حساب",
    "حل",
    "حلل",
    "اوجد",
    "جد",
    "وازن",
    "المعادله الموزونه",
    "اكتب المعادله",
    "اكمل المعادله",
    "حدد نوع",
    "المطلوب",
    "مساله",
    "تمرين",
    "تدريب",
    "اختبر نفسي",
    "نشاط",
    "كتاب الحلول",
    "الحلول",
    "عدد المولات",
    "الكتله الموليه",
    "التركيز",
    "حجم المحلول",
)

_TEXTBOOK_PATTERNS = (
    "ما هو",
    "ما هي",
    "ماهو",
    "ماهي",
    "عرف",
    "تعريف",
    "اشرح",
    "فسر",
    "لماذا",
    "قارن",
    "استنتج",
    "ما الفرق",
    "من الكتاب المدرسي",
    "الكتاب المدرسي",
)

_BOTH_PATTERNS = (
    "مع الحل",
    "ثم حل",
    "اشرح وحل",
    "عرف واحسب",
    "شرح الحل",
)

_ALIASES = {
    "answer_key": ROUTE_SOLUTIONS,
    "answer-key": ROUTE_SOLUTIONS,
    "solution": ROUTE_SOLUTIONS,
    "solutions_book": ROUTE_SOLUTIONS,
    "book": ROUTE_TEXTBOOK,
}


@dataclass(frozen=True)
class SourceRoute:
    """A deterministic routing decision for a student question."""

    route: str
    source_types: list[str]
    reason: str
    confidence: float
    matched_terms: list[str]
    cache_hit: bool = False


def normalize_query_text(text: str) -> str:
    """Normalize Arabic enough for intent/source keyword matching."""
    lowered = (text or "").lower().replace("ـ", "")
    lowered = _DIACRITICS_RE.sub("", lowered)
    lowered = lowered.translate(_ARABIC_NORMALIZATION)
    lowered = re.sub(r"[؟?!.،,؛;:()\[\]{}]+", " ", lowered)
    return " ".join(lowered.split()).strip()


def _normalize_requested_source_types(source_types: list[str] | None) -> list[str] | None:
    if not source_types:
        return None

    normalized: list[str] = []
    for raw_source_type in source_types:
        item = (raw_source_type or "").strip().lower()
        item = _ALIASES.get(item, item)
        if item in {"all", ROUTE_BOTH}:
            item = ROUTE_BOTH
        if item == ROUTE_BOTH:
            for source_type in (ROUTE_TEXTBOOK, ROUTE_SOLUTIONS):
                if source_type not in normalized:
                    normalized.append(source_type)
            continue
        if item in ROUTABLE_SOURCE_TYPES and item not in normalized:
            normalized.append(item)
    return normalized or None


def _contains_term(normalized_query: str, term: str) -> bool:
    if " " in term:
        return term in normalized_query
    pattern = rf"(?<![\u0621-\u064Aa-z0-9]){re.escape(term)}(?![\u0621-\u064Aa-z0-9])"
    return bool(re.search(pattern, normalized_query))


def _matched_terms(patterns: tuple[str, ...], normalized_query: str) -> list[str]:
    return [term for term in patterns if _contains_term(normalized_query, term)]


def _route_from_sources(source_types: list[str]) -> str:
    has_textbook = ROUTE_TEXTBOOK in source_types
    has_solutions = ROUTE_SOLUTIONS in source_types
    if has_textbook and has_solutions:
        return ROUTE_BOTH
    if has_solutions:
        return ROUTE_SOLUTIONS
    return ROUTE_TEXTBOOK


def route_source_sync(query: str, requested_source_types: list[str] | None = None) -> SourceRoute:
    """Route a query without external services; useful for tests and fallbacks."""
    explicit_sources = _normalize_requested_source_types(requested_source_types)
    if explicit_sources:
        return SourceRoute(
            route=_route_from_sources(explicit_sources),
            source_types=explicit_sources,
            reason="explicit_source_filter",
            confidence=1.0,
            matched_terms=[],
        )

    normalized = normalize_query_text(query)
    both_hits = _matched_terms(_BOTH_PATTERNS, normalized)
    solutions_hits = _matched_terms(_SOLUTIONS_PATTERNS, normalized)
    textbook_hits = _matched_terms(_TEXTBOOK_PATTERNS, normalized)

    if both_hits:
        return SourceRoute(
            route=ROUTE_BOTH,
            source_types=[ROUTE_TEXTBOOK, ROUTE_SOLUTIONS],
            reason="mixed_instruction",
            confidence=0.9,
            matched_terms=both_hits,
        )
    if solutions_hits and not textbook_hits:
        return SourceRoute(
            route=ROUTE_SOLUTIONS,
            source_types=[ROUTE_SOLUTIONS],
            reason="solution_or_calculation_keywords",
            confidence=0.86,
            matched_terms=solutions_hits,
        )
    if textbook_hits and not solutions_hits:
        return SourceRoute(
            route=ROUTE_TEXTBOOK,
            source_types=[ROUTE_TEXTBOOK],
            reason="concept_explanation_keywords",
            confidence=0.84,
            matched_terms=textbook_hits,
        )
    if solutions_hits and textbook_hits:
        return SourceRoute(
            route=ROUTE_BOTH,
            source_types=[ROUTE_TEXTBOOK, ROUTE_SOLUTIONS],
            reason="concept_and_solution_keywords",
            confidence=0.8,
            matched_terms=[*textbook_hits, *solutions_hits],
        )
    return SourceRoute(
        route=ROUTE_BOTH,
        source_types=[ROUTE_TEXTBOOK, ROUTE_SOLUTIONS],
        reason="default_both",
        confidence=0.55,
        matched_terms=[],
    )


async def route_source(query: str, requested_source_types: list[str] | None = None) -> SourceRoute:
    """Route a query and cache automatic decisions in Redis when available."""
    if requested_source_types:
        return route_source_sync(query, requested_source_types)

    cache_key = "source_router:" + _CACHE_VERSION + ":" + hashlib.sha256(
        normalize_query_text(query).encode("utf-8", errors="ignore")
    ).hexdigest()
    redis = get_redis_client()
    try:
        cached = await redis.get(cache_key)
        if cached:
            payload = json.loads(cached)
            payload["cache_hit"] = True
            return SourceRoute(**payload)
    except Exception:
        pass

    route = route_source_sync(query)
    try:
        await redis.setex(cache_key, _CACHE_TTL_SECONDS, json.dumps(asdict(route), ensure_ascii=False))
    except Exception:
        pass
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass
    return route
