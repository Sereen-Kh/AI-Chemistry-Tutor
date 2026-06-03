"""Chat orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import time
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import PROJECT_DIR, settings
from app.models.chat import ChatMessage, ChatSession
from app.services import ai_service
from app.services.chemistry_rules import answer_metal_dilute_acid_reaction, detect_metal_and_acid
from app.services.query_router import route_direct_answer
from app.services.rag import (
    RetrievedChunk,
    clean_query,
    format_context,
    lexical_relevance_score,
    retrieve_context,
    rewrite_query,
)

logger = logging.getLogger(__name__)

_QUESTION_PASSAGE_HINTS = ("؟", "السؤال", "اختر", "ضع اشارة", "المطلوب", "احسب", "اعط تفسير")
_LOW_VALUE_PASSAGE_HINTS = ("اهداف", "اﻫﺪاف", "الكلمات المفتاحية", "اﻟﻜﻠﻤﺎت", "نشاط", "ﻧﺸﺎط")
_PASSAGE_SPLIT_RE = re.compile(r"(?<=[.؟!])\s+")

# Lowered from 0.55 to 0.25 because hash-based fallback embeddings produce
# scores around 0.3–0.5 even for perfect lexical matches.  Raise to 0.45–0.55
# once real Gemini embeddings are active.
_MIN_BOOK_GROUNDED_CONFIDENCE = 0.25

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

_DEFINITION_TRIGGERS = ("ما هي", "ما هو", "ماهي", "ماهو", "عرف", "تعريف", "معنى")
_BOOK_GROUNDED_TRIGGERS = ("من الكتاب", "في الكتاب", "حسب الكتاب", "بحسب الكتاب", "من كتاب")
_FORMULA_TRIGGERS = ("صيغة", "الصيغة", "رمز", "الرمز", "formula")
_EQUATION_TRIGGERS = ("معادلة", "المعادلة", "وازن", "موزونة", "اكتب المعادلة")
_REACTION_TRIGGERS = ("تفاعل", "يتفاعل", "تتفاعل", "مع حمض", "مع الماء", "ناتج", "الناتج")
_TABLE_TRIGGERS = ("جدول", "الجدول", "سلسلة", "السلسلة")
_VALID_ANSWER_TYPES = {"auto", "text", "image", "video", "mixed"}
_EQUATION_LINE_RE = re.compile(
    r"(?=.*(?:→|⇌|->|=))(?=.*(?:[A-Z][a-z]?\d*|H2|HCl|H2SO4|NaOH|Cu|Fe|Zn|Mg|Al)).+"
)
_SOURCE_SLUG = "syria_grade_9_chemistry"
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


@dataclass(frozen=True)
class EntityDefinition:
    entity: str
    normalized_entity: str
    aliases: tuple[str, ...]
    rewrite: str
    definition: str
    example: str | None
    pages: tuple[int, ...]
    source_types: tuple[str, ...]
    litmus_property: str | None = None
    litmus_pages: tuple[int, ...] = ()


@dataclass(frozen=True)
class ChemistryDictionaryEntry:
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


_DEFINITION_ENTITIES: dict[str, EntityDefinition] = {
    "bases": EntityDefinition(
        entity="الأسس",
        normalized_entity="الاسس",
        aliases=(
            "الأسس",
            "الاسس",
            "الأساس",
            "الاساس",
            "اساس",
            "القواعد",
            "قاعدة",
            "قاعده",
            "المحاليل الأساسية",
            "المحاليل الاساسية",
            "OH-",
            "OH⁻",
        ),
        rewrite="تعريف الأسس الأساس أيونات الهدروكسيد OH- المحاليل الأساسية",
        definition="الأسس هي مواد تعطي عند انحلالها في الماء أيونات الهدروكسيد OH⁻.",
        example="مثال: هيدروكسيد الصوديوم NaOH وهيدروكسيد البوتاسيوم KOH.",
        pages=(19, 23),
        source_types=("definition", "learned_summary"),
        litmus_property="تلوّن المحاليل الأساسية ورقة عباد الشمس باللون الأزرق.",
        litmus_pages=(23,),
    ),
    "acids": EntityDefinition(
        entity="الحموض",
        normalized_entity="الحموض",
        aliases=(
            "الحموض",
            "حموض",
            "الأحماض",
            "الاحماض",
            "حمض",
            "المحاليل الحمضية",
            "المحاليل الحمضيه",
            "H+",
        ),
        rewrite="تعريف الحموض أيونات الهدروجين H+ المحاليل الحمضية",
        definition="الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+.",
        example="مثال: حمض كلور الماء HCl وحمض الكبريت H2SO4.",
        pages=(11, 13),
        source_types=("definition", "learned_summary"),
        litmus_property="تلوّن المحاليل الحمضية ورقة عباد الشمس باللون الأحمر.",
        litmus_pages=(13,),
    ),
}

_DEFINITION_CHUNK_PENALTY_MARKERS = (
    "الاهداف",
    "اﻫﺪاف",
    "يتعرف",
    "يتعرّف",
    "يميز",
    "يميّز",
    "احتياطات",
    "اثناء استعمال المحاليل",
)

_ANSWER_SCOPES = {"auto", "book_only", "tutor_general"}
_CHEMISTRY_DICTIONARY_PATH = PROJECT_DIR / "backend" / "app" / "services" / "chemistry_entities.json"
_CHEMISTRY_DICTIONARY_CACHE: list[ChemistryDictionaryEntry] | None = None


def _normalize_intent_text(text: str) -> str:
    text = text.lower().replace("ـ", "")
    text = _DIACRITICS_RE.sub("", text)
    text = text.translate(_ARABIC_NORMALIZATION)
    text = re.sub(r"[؟?!.،,؛;:]+", " ", text)
    return " ".join(text.split()).strip()


def _chemistry_dictionary() -> list[ChemistryDictionaryEntry]:
    global _CHEMISTRY_DICTIONARY_CACHE
    if _CHEMISTRY_DICTIONARY_CACHE is not None:
        return _CHEMISTRY_DICTIONARY_CACHE

    raw_items = json.loads(_CHEMISTRY_DICTIONARY_PATH.read_text(encoding="utf-8"))
    _CHEMISTRY_DICTIONARY_CACHE = [
        ChemistryDictionaryEntry(
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
    return _CHEMISTRY_DICTIONARY_CACHE


def _token_contains_symbol(normalized_question: str, normalized_alias: str) -> bool:
    if not re.fullmatch(r"[a-z0-9+\-]+", normalized_alias):
        return False
    return normalized_alias in re.findall(r"[a-z0-9+\-]+", normalized_question)


def _alias_matches_question(normalized_question: str, alias: str) -> bool:
    normalized_alias = _normalize_intent_text(alias)
    if not normalized_alias:
        return False
    if re.fullmatch(r"[a-z0-9+\-]+", normalized_alias) and len(normalized_alias) <= 3:
        return _token_contains_symbol(normalized_question, normalized_alias)
    return normalized_alias in normalized_question


def _dictionary_entry_for_question(
    question: str,
    *,
    intent: str | None = None,
) -> ChemistryDictionaryEntry | None:
    normalized = _normalize_intent_text(question)
    entries = [entry for entry in _chemistry_dictionary() if entry.approved and entry.grade_level == 9]
    if intent == "property_lookup":
        entries.sort(key=lambda entry: (entry.type != "property", -len(entry.entity_ar)))
    else:
        entries.sort(key=lambda entry: (entry.type == "property", -len(entry.entity_ar)))

    for entry in entries:
        if any(_alias_matches_question(normalized, alias) for alias in entry.aliases):
            return entry
    return None


def _explicit_book_requested(question: str) -> bool:
    normalized = _normalize_intent_text(question)
    return any(_normalize_intent_text(trigger) in normalized for trigger in _BOOK_GROUNDED_TRIGGERS)


def _normalize_answer_scope(answer_scope: str | None) -> str:
    normalized = (answer_scope or "auto").strip().lower()
    return normalized if normalized in _ANSWER_SCOPES else "auto"


def _definition_entity_for_question(question: str) -> EntityDefinition | None:
    normalized = _normalize_intent_text(question)
    for entity in _DEFINITION_ENTITIES.values():
        aliases = sorted(entity.aliases, key=len, reverse=True)
        if any(_normalize_intent_text(alias) in normalized for alias in aliases):
            return entity
    return None


def _classify_question(question: str) -> dict:
    normalized = _normalize_intent_text(question)
    entity = _definition_entity_for_question(question)
    entity_payload = {
        "entity": entity.entity if entity else None,
        "normalized_entity": entity.normalized_entity if entity else None,
    }

    if any(term in normalized for term in ("لون", "ورقه عباد", "عباد الشمس", "تلون")):
        return {"intent": "property_lookup", "answer_style": "direct", **entity_payload}

    base_intent = _classify_intent(question)
    if base_intent in {"formula_lookup", "equation_lookup", "reaction_query", "table_lookup"}:
        return {"intent": base_intent, "answer_style": "direct" if entity else "normal", **entity_payload}

    if (
        any(trigger in normalized for trigger in ("ما هي", "ما هو", "ماهي", "ماهو", "عرف", "تعريف"))
        or "اشرح معني" in normalized
        or "اشرح معنى" in normalized
    ):
        return {"intent": "definition_lookup", "answer_style": "direct", **entity_payload}

    return {"intent": base_intent, "answer_style": "normal", **entity_payload}


def _classify_intent(question: str) -> str:
    """Classify the user's intent to guide retrieval behaviour.

    Returns retrieval intents such as definition_lookup, formula_lookup,
    equation_lookup, reaction_query, table_lookup, book_grounded, or general.
    """
    normalized = question.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا")
    normalized_lower = normalized.lower()

    normalized_for_property = _normalize_intent_text(question)
    if any(term in normalized_for_property for term in ("لون", "ورقه عباد", "عباد الشمس", "تلون")):
        return "property_lookup"

    if any(trigger in normalized_lower for trigger in _EQUATION_TRIGGERS):
        return "equation_lookup"

    if any(trigger in normalized_lower for trigger in _REACTION_TRIGGERS):
        return "reaction_query"

    if any(trigger in normalized_lower for trigger in _FORMULA_TRIGGERS):
        return "formula_lookup"

    if any(trigger in normalized_lower for trigger in _TABLE_TRIGGERS):
        return "table_lookup"

    if any(trigger in normalized_lower for trigger in _BOOK_GROUNDED_TRIGGERS):
        # Also check if it's a definition within book-grounded request
        if any(trigger in normalized_lower for trigger in _DEFINITION_TRIGGERS):
            return "definition_lookup"
        return "book_grounded"

    if any(trigger in normalized_lower for trigger in _DEFINITION_TRIGGERS):
        return "definition_lookup"

    return "general"


def _select_answer_type(intent: str, preferred_answer_type: str | None = "auto") -> str:
    preferred = (preferred_answer_type or "auto").strip().lower()
    if preferred not in _VALID_ANSWER_TYPES:
        preferred = "auto"
    if preferred != "auto":
        return preferred
    if intent in {"equation_lookup", "reaction_query"}:
        return "mixed"
    if intent == "clarification":
        return "clarification"
    return "text"


def _page_image_url(page_number: int | None, source_slug: str = _SOURCE_SLUG) -> str | None:
    if page_number is None:
        return None
    image_path = PROJECT_DIR / "data" / "textbooks" / source_slug / "page_images" / f"page_{page_number:03d}.png"
    if not image_path.exists():
        return None
    return f"/media/books/{source_slug}/page_images/page_{page_number:03d}.png"


def _source_page_blocks(chunks: list[RetrievedChunk], page_numbers: list[int] | None = None) -> list[dict]:
    pages = page_numbers or sorted({chunk.page_number for chunk in chunks if chunk.page_number is not None})
    blocks: list[dict] = []
    for page in pages[:4]:
        image_url = _page_image_url(page)
        if image_url:
            blocks.append(
                {
                    "type": "source_page",
                    "content": f"صفحة {page}",
                    "page": page,
                    "image_url": image_url,
                    "metadata": {"source_slug": _SOURCE_SLUG},
                }
            )
    return blocks


def _source_blocks(chunks: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "book_id": chunk.source or _SOURCE_SLUG,
            "page": chunk.page_number,
            "chunk_id": chunk.id,
            "chunk_type": chunk.content_type,
            "score": round(float(chunk.similarity_score), 4),
        }
        for chunk in chunks
    ]


def _synthetic_source_blocks(entity: EntityDefinition, pages: tuple[int, ...] | list[int]) -> list[dict]:
    blocks = []
    source_types = entity.source_types or ("definition",)
    for index, page in enumerate(pages):
        blocks.append(
            {
                "book_id": _SOURCE_SLUG,
                "page": page,
                "chunk_id": 0,
                "chunk_type": source_types[min(index, len(source_types) - 1)],
                "score": 0.9,
            }
        )
    return blocks


def _chunk_preview(chunk: RetrievedChunk) -> str:
    return " ".join(chunk.content.split())[:180]


def _is_rejected_definition_chunk(chunk: RetrievedChunk) -> str | None:
    normalized = _normalize_intent_text(chunk.content)
    if chunk.content_type in {"objectives", "objective"}:
        return "objectives chunk does not answer definition question"
    if any(marker in normalized for marker in _DEFINITION_CHUNK_PENALTY_MARKERS):
        return "lesson objectives/safety text does not answer definition question"
    return None


def _definition_support_score(entity: EntityDefinition, chunk: RetrievedChunk) -> float:
    rejection = _is_rejected_definition_chunk(chunk)
    if rejection:
        return 0.0

    normalized = _normalize_intent_text(chunk.content)
    aliases = [_normalize_intent_text(alias) for alias in entity.aliases]
    has_entity_alias = any(alias and alias in normalized for alias in aliases)
    has_base_core = entity.normalized_entity == "الاسس" and (
        "ايونات الهدروكسيد" in normalized or "ايون الهدروكسيد" in normalized or "oh" in normalized
    )
    has_acid_core = entity.normalized_entity == "الحموض" and (
        "ايونات الهدروجين" in normalized or "ايون الهدروجين" in normalized or "h+" in normalized
    )
    has_definition_phrase = "مواد تعطي" in normalized or "انحلالها في الماء" in normalized
    if entity.normalized_entity == "الاسس" and not (has_base_core or (has_entity_alias and has_definition_phrase)):
        return 0.0
    if entity.normalized_entity == "الحموض" and not (has_acid_core or (has_entity_alias and has_definition_phrase)):
        return 0.0
    if not (has_entity_alias or has_base_core or has_acid_core):
        return 0.0

    score = 0.0
    if has_entity_alias:
        score += 0.25
    if "مواد تعطي" in normalized:
        score += 0.25
    if "انحلالها في الماء" in normalized:
        score += 0.20
    if has_base_core:
        score += 0.35
    if has_acid_core:
        score += 0.35
    if chunk.content_type in {"definition", "learned_summary", "result"}:
        score += 0.15
    return score


def _definition_context(
    entity: EntityDefinition,
    chunks: list[RetrievedChunk],
) -> tuple[list[RetrievedChunk], list[dict]]:
    rejected: list[dict] = []
    scored: list[tuple[float, RetrievedChunk]] = []
    for chunk in chunks:
        rejection = _is_rejected_definition_chunk(chunk)
        if rejection:
            rejected.append(
                {
                    "page": chunk.page_number,
                    "chunk_type": chunk.content_type,
                    "reason": rejection,
                    "content_preview": _chunk_preview(chunk),
                }
            )
            continue
        score = _definition_support_score(entity, chunk)
        if score > 0:
            scored.append((score, chunk))
        else:
            rejected.append(
                {
                    "page": chunk.page_number,
                    "chunk_type": chunk.content_type,
                    "reason": "chunk does not contain the required definition entity evidence",
                    "content_preview": _chunk_preview(chunk),
                }
            )

    scored.sort(key=lambda item: (item[0], item[1].similarity_score), reverse=True)
    return [chunk for _score, chunk in scored[:4]], rejected


def _retrieval_diagnostics(
    *,
    question: str,
    intent: str,
    entity: EntityDefinition | None,
    chunks: list[RetrievedChunk],
    rejected_chunks: list[dict] | None = None,
    confidence: float | None = None,
) -> dict:
    cleaned = clean_query(question)
    rewritten = entity.rewrite if entity else rewrite_query(cleaned)
    top_score = max((chunk.similarity_score for chunk in chunks), default=0.0)
    lexical_scores = [lexical_relevance_score(rewritten, chunk.content) for chunk in chunks]
    return {
        "original_query": question,
        "normalized_query": cleaned,
        "intent": intent,
        "entity": entity.entity if entity else None,
        "normalized_entity": entity.normalized_entity if entity else None,
        "rewritten_query": rewritten,
        "retrieved_chunks": [
            {
                "page": chunk.page_number,
                "chunk_type": chunk.content_type,
                "score": round(float(chunk.similarity_score), 4),
                "content_preview": _chunk_preview(chunk),
            }
            for chunk in chunks
        ],
        "rejected_chunks": rejected_chunks or [],
        "final_context": [
            {"page": chunk.page_number, "chunk_id": chunk.id, "chunk_type": chunk.content_type}
            for chunk in chunks
        ],
        "confidence_components": {
            "top_score": round(float(top_score), 4),
            "lexical_max": round(max(lexical_scores, default=0.0), 4),
            "final_confidence": confidence,
        },
        "gemini_available": bool(settings.effective_gemini_api_key),
    }


def _direct_definition_response(
    *,
    entity: EntityDefinition,
    chunks: list[RetrievedChunk],
    preferred_answer_type: str,
    diagnostics: dict,
    answer_scope: str = "auto",
    route: str = "textbook_rag",
    grounding: str = "book",
) -> dict:
    supporting_chunks, rejected_chunks = _definition_context(entity, chunks)
    pages = sorted({chunk.page_number for chunk in supporting_chunks if chunk.page_number is not None})
    if not pages:
        pages = list(entity.pages)

    confidence = 0.9 if supporting_chunks or entity.pages else 0.78
    text_blocks = [
        {"type": "text", "content": entity.definition, "page": None, "image_url": None, "metadata": {}}
    ]
    if entity.example:
        text_blocks.append({"type": "text", "content": entity.example, "page": None, "image_url": None, "metadata": {}})

    answer_type = _select_answer_type("definition_lookup", preferred_answer_type)
    if answer_type in {"image", "mixed"}:
        text_blocks.extend(_source_page_blocks(supporting_chunks, page_numbers=pages))

    answer = "\n\n".join(block["content"] for block in text_blocks if block["type"] == "text")
    answer = f"{answer}\n\nالمصدر: صفحة {'، '.join(str(page) for page in pages)}."
    diagnostics.update(
        _retrieval_diagnostics(
            question=diagnostics.get("original_query", ""),
            intent="definition_lookup",
            entity=entity,
            chunks=supporting_chunks or chunks,
            rejected_chunks=rejected_chunks,
            confidence=confidence,
        )
    )
    if not supporting_chunks:
        diagnostics["final_context"] = [
            {
                "page": page,
                "chunk_id": 0,
                "chunk_type": entity.source_types[min(index, len(entity.source_types) - 1)],
            }
            for index, page in enumerate(pages)
        ]
        diagnostics["selected_source_pages"] = pages
    diagnostics.update({"fallback_used": "definition_template", "answer_style": "direct"})
    diagnostics.update({"route": route, "grounding": grounding, "answer_scope": answer_scope})

    return {
        "answer": answer,
        "answer_type": answer_type,
        "route": route,
        "grounding": grounding,
        "answer_scope": answer_scope,
        "blocks": text_blocks,
        "sources": supporting_chunks,
        "source_blocks": _source_blocks(supporting_chunks) or _synthetic_source_blocks(entity, pages),
        "page_numbers": pages,
        "confidence": round(float(confidence), 4),
        "diagnostics": diagnostics,
        "suggested_next_action": "يمكنك أن تسأل عن الفرق بين الأسس القوية والضعيفة." if entity.normalized_entity == "الاسس" else "يمكنك أن تسأل عن الحموض القوية والضعيفة.",
    }


def _direct_property_response(
    *,
    entity: EntityDefinition,
    preferred_answer_type: str,
    diagnostics: dict,
) -> dict | None:
    if not entity.litmus_property:
        return None
    pages = list(entity.litmus_pages or entity.pages)
    answer_type = _select_answer_type("property_lookup", preferred_answer_type)
    blocks = [{"type": "text", "content": entity.litmus_property, "page": None, "image_url": None, "metadata": {}}]
    if answer_type in {"image", "mixed"}:
        blocks.extend(_source_page_blocks([], page_numbers=pages))
    answer = f"{entity.litmus_property}\n\nالمصدر: صفحة {'، '.join(str(page) for page in pages)}."
    diagnostics.update(
        _retrieval_diagnostics(
            question=diagnostics.get("original_query", ""),
            intent="property_lookup",
            entity=entity,
            chunks=[],
            confidence=0.88,
        )
    )
    diagnostics.update(
        {
            "intent": "property_lookup",
            "entity": entity.entity,
            "normalized_entity": entity.normalized_entity,
            "fallback_used": "property_template",
            "answer_style": "direct",
            "gemini_available": bool(settings.effective_gemini_api_key),
        }
    )
    return {
        "answer": answer,
        "answer_type": answer_type,
        "route": "dictionary_first",
        "grounding": "approved_dictionary",
        "answer_scope": diagnostics.get("answer_scope", "auto"),
        "blocks": blocks,
        "sources": [],
        "source_blocks": _synthetic_source_blocks(entity, pages),
        "page_numbers": pages,
        "confidence": 0.88,
        "diagnostics": diagnostics,
        "suggested_next_action": "يمكنك أن تسأل عن تجربة التمييز بين الحموض والأسس بورقة عباد الشمس.",
    }


def _valid_book_chunks_for_dictionary_entry(
    entry: ChemistryDictionaryEntry,
    chunks: list[RetrievedChunk],
) -> tuple[list[RetrievedChunk], list[dict]]:
    valid: list[RetrievedChunk] = []
    rejected: list[dict] = []
    normalized_terms = [_normalize_intent_text(term) for term in entry.book_validation_terms]
    for chunk in chunks:
        normalized_content = _normalize_intent_text(chunk.content)
        if any(term and term in normalized_content for term in normalized_terms):
            valid.append(chunk)
        else:
            rejected.append(
                {
                    "page": chunk.page_number,
                    "chunk_type": chunk.content_type,
                    "reason": f"chunk does not contain exact evidence for {entry.entity_ar}",
                    "content_preview": _chunk_preview(chunk),
                }
            )
    return valid, rejected


def _dictionary_source_blocks(entry: ChemistryDictionaryEntry, chunks: list[RetrievedChunk] | None = None) -> list[dict]:
    if chunks:
        return _source_blocks(chunks)
    return [
        {
            "book_id": entry.source_type,
            "page": None,
            "chunk_id": 0,
            "chunk_type": entry.type,
            "score": round(float(entry.confidence), 4),
        }
    ]


def _dictionary_answer_text(
    entry: ChemistryDictionaryEntry,
    *,
    label: str | None = None,
) -> str:
    parts = []
    if label:
        parts.append(label)
    parts.append(entry.answer_ar)
    if entry.formula and entry.formula not in entry.answer_ar:
        parts.append(f"الصيغة: {entry.formula}.")
    if entry.symbol and entry.symbol not in entry.answer_ar:
        parts.append(f"الرمز: {entry.symbol}.")
    return "\n\n".join(parts)


def _dictionary_response(
    *,
    entry: ChemistryDictionaryEntry,
    question: str,
    answer_scope: str,
    preferred_answer_type: str,
    route: str,
    grounding: str,
    diagnostics: dict,
    chunks: list[RetrievedChunk] | None = None,
    label: str | None = None,
    rejected_chunks: list[dict] | None = None,
) -> dict:
    pages = sorted({chunk.page_number for chunk in chunks or [] if chunk.page_number is not None})
    answer = _dictionary_answer_text(entry, label=label)
    answer_type = _select_answer_type("property_lookup" if entry.type == "property" else "definition_lookup", preferred_answer_type)
    blocks = [{"type": "text", "content": answer, "page": None, "image_url": None, "metadata": {}}]
    if answer_type in {"image", "mixed"} and pages:
        blocks.extend(_source_page_blocks(chunks or [], page_numbers=pages))

    diagnostics.update(
        _retrieval_diagnostics(
            question=question,
            intent=diagnostics.get("intent", "definition_lookup"),
            entity=None,
            chunks=chunks or [],
            rejected_chunks=rejected_chunks,
            confidence=entry.confidence,
        )
    )
    diagnostics.update(
        {
            "route": route,
            "grounding": grounding,
            "answer_scope": answer_scope,
            "dictionary_entry_id": entry.id,
            "dictionary_source_type": entry.source_type,
            "fallback_used": "approved_dictionary",
        }
    )
    return {
        "answer": answer,
        "answer_type": answer_type,
        "route": route,
        "grounding": grounding,
        "answer_scope": answer_scope,
        "blocks": blocks,
        "sources": chunks or [],
        "source_blocks": _dictionary_source_blocks(entry, chunks),
        "page_numbers": pages,
        "confidence": round(float(entry.confidence), 4),
        "diagnostics": diagnostics,
        "suggested_next_action": "يمكنك أن تطلب مثالاً أو سؤالاً تدريبياً مرتبطاً.",
    }


def _not_found_response(
    *,
    question: str,
    answer_scope: str,
    preferred_answer_type: str,
    diagnostics: dict,
    chunks: list[RetrievedChunk] | None = None,
    rejected_chunks: list[dict] | None = None,
) -> dict:
    answer = "لم أجد ذلك بوضوح في مقاطع الكتاب المتاحة."
    diagnostics.update(
        _retrieval_diagnostics(
            question=question,
            intent=diagnostics.get("intent", "general"),
            entity=None,
            chunks=chunks or [],
            rejected_chunks=rejected_chunks,
            confidence=0.0,
        )
    )
    diagnostics.update({"route": "not_found", "grounding": "book", "answer_scope": answer_scope})
    return {
        "answer": answer,
        "answer_type": "not_found",
        "route": "not_found",
        "grounding": "book",
        "answer_scope": answer_scope,
        "blocks": _build_answer_blocks(
            answer,
            chunks or [],
            answer_type="not_found",
            preferred_answer_type=preferred_answer_type,
            diagnostics=diagnostics,
        ),
        "sources": chunks or [],
        "source_blocks": _source_blocks(chunks or []),
        "page_numbers": sorted({chunk.page_number for chunk in chunks or [] if chunk.page_number is not None}),
        "confidence": 0.0,
        "diagnostics": diagnostics,
        "suggested_next_action": "أعد صياغة السؤال أو جرّب سؤالاً موجوداً نصاً في الكتاب.",
    }


def _append_text_block(blocks: list[dict], lines: list[str]) -> None:
    content = "\n".join(line for line in lines if line.strip()).strip()
    if content:
        blocks.append({"type": "text", "content": content, "page": None, "image_url": None, "metadata": {}})


def _build_answer_blocks(
    answer: str,
    chunks: list[RetrievedChunk],
    *,
    answer_type: str,
    preferred_answer_type: str | None = "auto",
    page_numbers: list[int] | None = None,
    diagnostics: dict | None = None,
) -> list[dict]:
    """Convert an answer string and sources into structured frontend blocks."""
    blocks: list[dict] = []
    pending_text: list[str] = []
    for raw_line in answer.splitlines():
        line = raw_line.strip()
        if not line:
            pending_text.append("")
            continue
        if _EQUATION_LINE_RE.match(line):
            _append_text_block(blocks, pending_text)
            pending_text = []
            blocks.append(
                {
                    "type": "equation",
                    "content": line,
                    "page": None,
                    "image_url": None,
                    "metadata": {"direction": "ltr"},
                }
            )
        else:
            pending_text.append(raw_line)
    _append_text_block(blocks, pending_text)

    if not blocks:
        block_type = "clarification" if answer_type == "clarification" else "text"
        blocks.append({"type": block_type, "content": answer, "page": None, "image_url": None, "metadata": {}})
    elif answer_type == "clarification" and blocks[0]["type"] == "text":
        blocks[0]["type"] = "clarification"

    source_pages = _source_page_blocks(chunks, page_numbers=page_numbers)
    if answer_type in {"image", "mixed"} or (preferred_answer_type == "image" and source_pages):
        blocks.extend(source_pages)

    if preferred_answer_type == "video":
        blocks.append(
            {
                "type": "video_script",
                "content": (
                    "شرح فيديو مقترح:\n"
                    "1. عرض السؤال والمعادلة.\n"
                    "2. تحديد موقع المعدن بالنسبة للهيدروجين في سلسلة النشاط.\n"
                    "3. استنتاج هل يحدث التفاعل ثم كتابة النتيجة."
                ),
                "page": None,
                "image_url": None,
                "metadata": {"generated": False, "reason": "video_url_not_available", **(diagnostics or {})},
            }
        )

    return blocks


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _compute_confidence(
    question: str,
    chunks: list[RetrievedChunk],
) -> float:
    """Compute a confidence score that blends vector similarity with lexical matching.

    This prevents strong lexical matches from being rejected when the vector
    similarity is low (e.g. with fallback hash-based embeddings).
    """
    if not chunks:
        return 0.0

    cleaned = clean_query(question)

    # Raw max from hybrid scoring
    raw_max = max((c.similarity_score for c in chunks), default=0.0)

    # Independent lexical check against chunk contents
    lexical_scores = []
    for chunk in chunks:
        lex = lexical_relevance_score(cleaned, chunk.content)
        lexical_scores.append(lex)
    lexical_max = max(lexical_scores, default=0.0)

    confidence = max(raw_max, lexical_max * 0.9)

    # Boost if multiple relevant pages found (indicates strong coverage)
    relevant_pages = {c.page_number for c in chunks if c.page_number and c.similarity_score > 0.15}
    if len(relevant_pages) >= 2:
        confidence = min(confidence + 0.10, 1.0)

    # Boost for exact term matches in definitions
    combined_content = " ".join(c.content for c in chunks[:3])
    combined_norm = combined_content.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا").replace("ة", "ه")
    question_norm = cleaned.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا").replace("ة", "ه")
    # Check if key content terms from the question appear in chunk text
    key_terms = [t for t in re.findall(r"[\u0621-\u064A]{3,}", question_norm) if len(t) > 3]
    matched_key = sum(1 for t in key_terms if t in combined_norm)
    if key_terms and matched_key / len(key_terms) > 0.5:
        confidence = min(confidence + 0.15, 1.0)

    return round(confidence, 4)


# ---------------------------------------------------------------------------
# Source-grounded system prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_WITH_CONTEXT = (
    "أنت مدرس كيمياء للصف التاسع. أجب بالاعتماد حصرياً على المقاطع التالية من الكتاب.\n"
    "التعليمات:\n"
    "1. استخدم فقط المعلومات الموجودة في المقاطع أدناه.\n"
    "2. اذكر رقم الصفحة لكل معلومة تستخدمها بالشكل: (صفحة XX).\n"
    "3. إذا لم تجد الإجابة في المقاطع، قل ذلك بوضوح.\n"
    "4. لا تخترع معلومات أو مصادر غير موجودة في المقاطع.\n"
    "5. رتب إجابتك: التعريف أولاً، ثم التفاصيل، ثم الأمثلة.\n\n"
    "المقاطع:\n{context}"
)

_SYSTEM_PROMPT_NO_CONTEXT = (
    "أنت مدرس كيمياء للصف التاسع. أجب بالعربية.\n"
    "إذا لم تكن الإجابة موجودة في مصادر الكتاب أو الامتحانات المتاحة، "
    "قل بوضوح إنك لم تجدها في المصادر المتاحة، ثم يمكنك تقديم شرح عام منفصل."
)

_SYSTEM_PROMPT_ASK_WITH_CONTEXT = (
    "أنت مدرس كيمياء للصف التاسع. أجب بالاعتماد على المصادر التالية.\n"
    "اذكر رقم الصفحة عندما يكون متاحاً. لا تخترع مصادر.\n\n"
    "المقاطع:\n{context}"
)

_SYSTEM_PROMPT_ASK_NO_CONTEXT = (
    "أنت مدرس كيمياء للصف التاسع. أجب بالعربية.\n"
    "اذكر بوضوح أن السياق المدرسي المتاح غير كاف إذا لم تجد مصدراً."
)


# ---------------------------------------------------------------------------
# Passage helpers (unchanged logic, preserved for backward compat)
# ---------------------------------------------------------------------------

def _clean_passage(text: str) -> str:
    return " ".join(text.split()).strip(" -•")


def _clean_display_arabic(text: str) -> str:
    """Lightly clean common PDF extraction artifacts for user-facing fallback text."""
    replacements = {
        "انحالل": "انحلال",
        "االنحلال": "الانحلال",
        "اأ": "الأ",
        "اإ": "الإ",
        "اآ": "الآ",
        "أيَّونات": "أيونات",
        "الصّ يغة": "الصيغة",
        "الحمضيَّة": "الحمضية",
        "تتأيَّن": "تتأين",
        "تأيّناً": "تأيناً",
        "جزئياُ": "جزئياً",
        "عبَّاد": "عباد",
        "الشَّمس": "الشمس",
    }
    cleaned = _clean_passage(text)
    cleaned = cleaned.lstrip(".:؛، ")
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"\s+([،؛؟.!:])", r"\1", cleaned)
    cleaned = re.sub(r"([،؛؟.!:])(?=\S)", r"\1 ", cleaned)
    return cleaned


def _split_passages(content: str) -> list[str]:
    passages: list[str] = []
    for raw_line in content.splitlines():
        line = _clean_passage(raw_line)
        if not line:
            continue
        if len(line) > 260:
            passages.extend(_clean_passage(item) for item in _PASSAGE_SPLIT_RE.split(line) if _clean_passage(item))
        else:
            passages.append(line)
    return passages


def _relevant_book_passages(question: str, chunks: list[RetrievedChunk], max_items: int = 5) -> list[tuple[int | None, str]]:
    scored: list[tuple[float, int, int | None, str]] = []
    for chunk_index, chunk in enumerate(chunks):
        for passage in _split_passages(chunk.content):
            if len(passage) < 18:
                continue
            score = lexical_relevance_score(question, passage)
            if score <= 0:
                continue
            normalized = passage.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا")
            if any(hint in normalized for hint in _QUESTION_PASSAGE_HINTS):
                score *= 0.45
            if any(hint in normalized for hint in _LOW_VALUE_PASSAGE_HINTS):
                score *= 0.35
            scored.append((score, chunk_index, chunk.page_number, passage))

    scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    seen: set[str] = set()
    selected: list[tuple[int | None, str]] = []
    for _score, _chunk_index, page_number, passage in scored:
        key = re.sub(r"\W+", "", passage.lower())[:120]
        if key in seen:
            continue
        seen.add(key)
        selected.append((page_number, passage))
        if len(selected) >= max_items:
            break
    return selected


def _is_acids_question(question: str) -> bool:
    normalized = question.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا").replace("ة", "ه")
    return any(term in normalized for term in ("حموض", "حمض", "احماض", "الاحماض"))


def _acid_answer_from_chunks(chunks: list[RetrievedChunk]) -> str | None:
    """Build a readable deterministic answer when the acid definition is present in retrieved chunks."""
    combined = "\n".join(chunk.content for chunk in chunks)
    normalized = combined.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا").replace("ة", "ه")
    if "الحموض" not in normalized and "حمض" not in normalized:
        return None

    pages = sorted({chunk.page_number for chunk in chunks if chunk.page_number is not None})
    selected_pages = "، ".join(str(page) for page in pages if page in {11, 13, 15}) or "، ".join(str(page) for page in pages)
    return (
        "من الكتاب:\n"
        "الحموض هي مواد تعطي عند انحلالها في الماء أيونات الهدروجين H+.\n\n"
        "النقاط الأساسية:\n"
        "- تحتوي الحموض في صيغتها الأيونية على أيون الهدروجين H+.\n"
        "- عدد الوظائف الحمضية هو عدد أيونات الهدروجين في الصيغة الأيونية للحمض.\n"
        "- الحموض القوية تتأين كلياً في الماء، مثل حمض كلور الماء وحمض الكبريت.\n"
        "- الحموض الضعيفة تتأين جزئياً في الماء، مثل حمض الخل وحمض النمل وحمض الكربون.\n"
        "- تكشف المحاليل الحمضية بورقة عباد الشمس؛ فهي تلونها باللون الأحمر.\n\n"
        f"المصادر: صفحة {selected_pages}."
    )


def _local_rag_answer(question: str, chunks: list[RetrievedChunk], reason: str | None = None) -> str:
    """Build a useful source-backed fallback when no Gemini key is configured."""
    intro = "إجابة مبنية على مقاطع الكتاب المتاحة."
    if not chunks:
        return (
            f"{intro}\n\n"
            "لم أجد مقاطع كافية من الكتاب للإجابة عن السؤال بدقة."
        )

    if _is_acids_question(question):
        answer = _acid_answer_from_chunks(chunks)
        if answer:
            return answer

    references = sorted({chunk.page_number for chunk in chunks if chunk.page_number is not None})
    relevant_passages = _relevant_book_passages(question, chunks)
    if relevant_passages:
        answer_lines = []
        for page_number, passage in relevant_passages:
            page = f"صفحة {page_number}" if page_number else "مصدر من الكتاب"
            answer_lines.append(f"- {_clean_display_arabic(passage)} ({page})")
        pages = "، ".join(str(page) for page in references) if references else "غير محددة"
        return (
            f"{intro}\n\n"
            "إجابة من مقاطع الكتاب:\n"
            + "\n".join(answer_lines)
            + f"\n\nالمصادر: صفحة {pages}."
        )

    excerpts = []
    for chunk in chunks[:3]:
        text = " ".join(chunk.content.split())
        if len(text) > 360:
            text = f"{text[:360]}..."
        page = f"صفحة {chunk.page_number}" if chunk.page_number else "مصدر من الكتاب"
        excerpts.append(f"- {page}: {text}")

    pages = "، ".join(str(page) for page in references) if references else "غير محددة"
    return (
        f"{intro}\n\n"
        f"السؤال: {question}\n\n"
        "أقرب مقاطع وجدتها من كتاب الكيمياء:\n"
        + "\n".join(excerpts)
        + f"\n\nالصفحات المرتبطة: {pages}\n"
        "هذه ليست إجابة مولدة بالكامل، لكنها تعرض المصادر التي وجدها نظام RAG."
    )


async def _answer_with_rag_fallback(
    *,
    messages: list[dict[str, str]],
    question: str,
    chunks: list[RetrievedChunk],
    system_prompt: str,
) -> str:
    if not settings.effective_gemini_api_key:
        return _local_rag_answer(question, chunks)

    try:
        answer = await ai_service.get_ai_response(messages, system_prompt=system_prompt, raise_on_error=True)
        if answer.strip():
            return answer
        return _local_rag_answer(
            question,
            chunks,
            reason="عاد Gemini برد فارغ حالياً، لذلك أعرض لك إجابة محلية من مصادر الكتاب.",
        )
    except ai_service.AIQuotaExceededError:
        logger.info("Gemini quota exceeded; using local RAG fallback.")
        return _local_rag_answer(
            question,
            chunks,
            reason="local_rag",
        )
    except ai_service.AIServiceError:
        logger.info("Gemini service failed; using local RAG fallback.")
        return _local_rag_answer(
            question,
            chunks,
            reason="local_rag",
        )


async def create_session(
    db: AsyncSession,
    user_id: int,
    title: str = "محادثة جديدة",
    lesson_id: int | None = None,
    style: str | None = None,
) -> ChatSession:
    """Create a new chat session for a user."""
    session = ChatSession(user_id=user_id, title=title, lesson_id=lesson_id, style=style)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_user_sessions(db: AsyncSession, user_id: int) -> list[ChatSession]:
    """Return all chat sessions for a user."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_owned_session(db: AsyncSession, session_id: int, user_id: int) -> ChatSession:
    """Load a chat session and verify the current user owns it."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    session = result.scalars().first()
    if session is None or session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


async def send_message(
    db: AsyncSession,
    session_id: int,
    user_id: int,
    content: str,
    message_format: str = "text",
) -> ChatMessage:
    """Save a user message, retrieve RAG context, generate and save an AI reply."""
    session = await get_owned_session(db, session_id, user_id)
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=content,
        format=message_format,
    )
    db.add(user_message)
    await db.flush()

    intent = _classify_intent(content)
    logger.info("Chat intent classified: %s for query: %s", intent, content[:80])

    chunks = await retrieve_context(db, content, user_id=user_id, top_k=6, min_similarity=0.0, intent=intent)
    context = format_context(chunks)

    if context:
        system_prompt = _SYSTEM_PROMPT_WITH_CONTEXT.format(context=context)
    else:
        system_prompt = _SYSTEM_PROMPT_NO_CONTEXT

    history = [
        {"role": message.role, "content": message.content}
        for message in session.messages
        if message.role in {"user", "assistant"}
    ]
    if not history or history[-1]["content"] != content:
        history.append({"role": "user", "content": content})

    start = time.time()
    answer = await _answer_with_rag_fallback(
        messages=history,
        question=content,
        chunks=chunks,
        system_prompt=system_prompt,
    )
    latency_ms = int((time.time() - start) * 1000)

    assistant_message = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        latency_ms=latency_ms,
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    return assistant_message


async def ask_question(
    db: AsyncSession,
    user_id: int,
    question: str,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    source_types: list[str] | None = None,
    preferred_answer_type: str = "auto",
    answer_scope: str = "auto",
) -> dict:
    """Answer a one-off question with RAG sources."""
    answer_scope = _normalize_answer_scope(answer_scope)
    classification = _classify_question(question)
    intent = classification["intent"]
    entity = _definition_entity_for_question(question)
    explicit_book = _explicit_book_requested(question)
    dictionary_entry = _dictionary_entry_for_question(question, intent=intent)
    metal, acid = detect_metal_and_acid(question)
    diagnostics: dict = {
        "original_query": question,
        "normalized_query": clean_query(question),
        "intent": intent,
        "entity": classification.get("entity"),
        "normalized_entity": classification.get("normalized_entity"),
        "answer_style": classification.get("answer_style"),
        "preferred_answer_type": preferred_answer_type,
        "answer_scope": answer_scope,
        "explicit_book_requested": explicit_book,
        "dictionary_entry_id": dictionary_entry.id if dictionary_entry else None,
        "reactants": {
            "metal": metal.symbol if metal else None,
            "acid": acid.formula if acid else None,
        },
        "gemini_available": bool(settings.effective_gemini_api_key),
    }

    simple_dictionary_intents = {"definition_lookup", "formula_lookup", "property_lookup"}
    if (
        dictionary_entry
        and answer_scope in {"auto", "tutor_general"}
        and not explicit_book
        and (intent in simple_dictionary_intents or answer_scope == "tutor_general")
    ):
        return _dictionary_response(
            entry=dictionary_entry,
            question=question,
            answer_scope=answer_scope,
            preferred_answer_type=preferred_answer_type,
            route="dictionary_first",
            grounding="approved_dictionary" if answer_scope == "auto" else "general_tutor",
            diagnostics=diagnostics,
        )

    if intent == "property_lookup" and entity and answer_scope != "book_only" and not explicit_book:
        property_response = _direct_property_response(
            entity=entity,
            preferred_answer_type=preferred_answer_type,
            diagnostics=diagnostics,
        )
        if property_response:
            return property_response

    reaction_answer = answer_metal_dilute_acid_reaction(question)
    if reaction_answer and answer_scope != "book_only":
        answer_type = _select_answer_type(reaction_answer.intent, preferred_answer_type)
        diagnostics.update(
            {
                "intent": reaction_answer.intent,
                "route": "dictionary_first",
                "grounding": "approved_dictionary",
                "rule_engine": "activity_series",
                "reaction_happens": reaction_answer.reaction_happens,
                "equation": reaction_answer.equation,
                "warnings": reaction_answer.warnings,
            }
        )
        return {
            "answer": reaction_answer.answer,
            "answer_type": answer_type,
            "route": "dictionary_first",
            "grounding": "approved_dictionary",
            "answer_scope": answer_scope,
            "blocks": _build_answer_blocks(
                reaction_answer.answer,
                [],
                answer_type=answer_type,
                preferred_answer_type=preferred_answer_type,
                page_numbers=reaction_answer.page_numbers,
                diagnostics=diagnostics,
            ),
            "sources": [],
            "source_blocks": [],
            "page_numbers": reaction_answer.page_numbers,
            "confidence": round(float(reaction_answer.confidence), 4),
            "diagnostics": diagnostics,
            "suggested_next_action": reaction_answer.suggested_next_action,
        }

    direct_answer = route_direct_answer(question)
    if direct_answer and answer_scope != "book_only":
        answer_type = _select_answer_type(direct_answer.intent, preferred_answer_type)
        diagnostics.update(
            {
                "intent": direct_answer.intent,
                "rule_engine": "direct_router",
                "route": "dictionary_first",
                "grounding": "approved_dictionary",
            }
        )
        return {
            "answer": direct_answer.answer,
            "answer_type": answer_type,
            "route": "dictionary_first",
            "grounding": "approved_dictionary",
            "answer_scope": answer_scope,
            "blocks": _build_answer_blocks(
                direct_answer.answer,
                [],
                answer_type=answer_type,
                preferred_answer_type=preferred_answer_type,
                page_numbers=direct_answer.page_numbers,
                diagnostics=diagnostics,
            ),
            "sources": [],
            "source_blocks": [],
            "page_numbers": direct_answer.page_numbers,
            "confidence": direct_answer.confidence,
            "diagnostics": diagnostics,
            "suggested_next_action": direct_answer.suggested_next_action,
        }

    logger.info("Ask intent classified: %s for query: %s", intent, question[:80])
    if dictionary_entry and (explicit_book or answer_scope == "book_only"):
        retrieval_question = f"{dictionary_entry.entity_ar} {' '.join(dictionary_entry.book_validation_terms)}"
    elif entity and intent == "definition_lookup":
        retrieval_question = entity.rewrite
    else:
        retrieval_question = question

    chunks = await retrieve_context(
        db,
        retrieval_question,
        user_id=user_id,
        lesson_id=lesson_id,
        topic_id=topic_id,
        source_types=source_types,
        top_k=6,
        intent=intent,
    )
    page_numbers = sorted({chunk.page_number for chunk in chunks if chunk.page_number is not None})
    diagnostics.update(
        {
            "retrieved_chunk_ids": [chunk.id for chunk in chunks],
            "retrieved_pages": page_numbers,
            "top_score": max((chunk.similarity_score for chunk in chunks), default=0.0),
        }
    )
    diagnostics.update(
        _retrieval_diagnostics(
            question=question,
            intent=intent,
            entity=entity,
            chunks=chunks,
        )
    )

    # Use the new confidence formula that blends vector + lexical scores
    confidence = _compute_confidence(question, chunks)

    dictionary_valid_chunks: list[RetrievedChunk] = []
    dictionary_rejected_chunks: list[dict] = []
    if dictionary_entry:
        dictionary_valid_chunks, dictionary_rejected_chunks = _valid_book_chunks_for_dictionary_entry(
            dictionary_entry,
            chunks,
        )

    if dictionary_entry and (explicit_book or answer_scope == "book_only"):
        if answer_scope == "book_only":
            if not dictionary_valid_chunks:
                return _not_found_response(
                    question=question,
                    answer_scope=answer_scope,
                    preferred_answer_type=preferred_answer_type,
                    diagnostics=diagnostics,
                    chunks=chunks,
                    rejected_chunks=dictionary_rejected_chunks,
                )
            book_answer = _local_rag_answer(question, dictionary_valid_chunks)
            book_confidence = _compute_confidence(question, dictionary_valid_chunks)
            diagnostics.update(
                _retrieval_diagnostics(
                    question=question,
                    intent=intent,
                    entity=None,
                    chunks=dictionary_valid_chunks,
                    rejected_chunks=dictionary_rejected_chunks,
                    confidence=book_confidence,
                )
            )
            diagnostics.update(
                {
                    "route": "textbook_rag",
                    "grounding": "book",
                    "answer_scope": answer_scope,
                    "book_exact_match": True,
                }
            )
            page_numbers = sorted(
                {chunk.page_number for chunk in dictionary_valid_chunks if chunk.page_number is not None}
            )
            answer_type = _select_answer_type(intent, preferred_answer_type)
            return {
                "answer": book_answer,
                "answer_type": answer_type,
                "route": "textbook_rag",
                "grounding": "book",
                "answer_scope": answer_scope,
                "blocks": _build_answer_blocks(
                    book_answer,
                    dictionary_valid_chunks,
                    answer_type=answer_type,
                    preferred_answer_type=preferred_answer_type,
                    page_numbers=page_numbers,
                    diagnostics=diagnostics,
                ),
                "sources": dictionary_valid_chunks,
                "source_blocks": _source_blocks(dictionary_valid_chunks),
                "page_numbers": page_numbers,
                "confidence": round(float(book_confidence), 4),
                "diagnostics": diagnostics,
                "suggested_next_action": "يمكنك أن تسأل عن مصدر آخر من الكتاب.",
            }

        if dictionary_valid_chunks:
            return _dictionary_response(
                entry=dictionary_entry,
                question=question,
                answer_scope=answer_scope,
                preferred_answer_type=preferred_answer_type,
                route="book_supported_dictionary",
                grounding="mixed",
                diagnostics=diagnostics,
                chunks=dictionary_valid_chunks,
                rejected_chunks=dictionary_rejected_chunks,
            )
        return _dictionary_response(
            entry=dictionary_entry,
            question=question,
            answer_scope=answer_scope,
            preferred_answer_type=preferred_answer_type,
            route="book_first",
            grounding="approved_dictionary",
            diagnostics=diagnostics,
            chunks=[],
            label="لم أجد ذلك بوضوح في مقاطع الكتاب المسترجعة، لكن من القاموس الكيميائي المعتمد:",
            rejected_chunks=dictionary_rejected_chunks,
        )

    if intent == "definition_lookup" and entity:
        supporting_chunks, rejected_chunks = _definition_context(entity, chunks)
        if answer_scope == "book_only" and not supporting_chunks:
            return _not_found_response(
                question=question,
                answer_scope=answer_scope,
                preferred_answer_type=preferred_answer_type,
                diagnostics=diagnostics,
                chunks=chunks,
                rejected_chunks=rejected_chunks,
            )
        return _direct_definition_response(
            entity=entity,
            chunks=chunks,
            preferred_answer_type=preferred_answer_type,
            diagnostics=diagnostics,
            answer_scope=answer_scope,
            route="textbook_rag" if supporting_chunks else "book_first",
            grounding="book" if supporting_chunks else "approved_dictionary",
        )

    if confidence < _MIN_BOOK_GROUNDED_CONFIDENCE:
        if answer_scope == "book_only":
            return _not_found_response(
                question=question,
                answer_scope=answer_scope,
                preferred_answer_type=preferred_answer_type,
                diagnostics=diagnostics,
                chunks=chunks,
            )
        answer = (
            "لم أجد ذلك بوضوح في مقاطع الكتاب المتاحة.\n\n"
            "يمكنني الإجابة عندما تحدد الدرس أو تستخدم صياغة أوضح، "
            "أما الآن فلا أريد أن أعطيك جواباً منسوباً للكتاب بثقة ضعيفة."
        )
        answer_type = "not_found"
        diagnostics.update({"low_confidence": True, "confidence_threshold": _MIN_BOOK_GROUNDED_CONFIDENCE})
        diagnostics["confidence_components"]["final_confidence"] = round(float(confidence), 4)
        return {
            "answer": answer,
            "answer_type": answer_type,
            "route": "not_found",
            "grounding": "book",
            "answer_scope": answer_scope,
            "blocks": _build_answer_blocks(
                answer,
                chunks,
                answer_type=answer_type,
                preferred_answer_type=preferred_answer_type,
                page_numbers=page_numbers,
                diagnostics=diagnostics,
            ),
            "sources": chunks,
            "source_blocks": _source_blocks(chunks),
            "page_numbers": page_numbers,
            "confidence": round(float(confidence), 4),
            "diagnostics": diagnostics,
            "suggested_next_action": "جرّب تحديد الدرس أو اسأل عن صيغة/تعريف/معادلة محددة.",
        }

    context = format_context(chunks)
    if context:
        system_prompt = _SYSTEM_PROMPT_ASK_WITH_CONTEXT.format(context=context)
    else:
        system_prompt = _SYSTEM_PROMPT_ASK_NO_CONTEXT

    answer = await _answer_with_rag_fallback(
        messages=[{"role": "user", "content": question}],
        question=question,
        chunks=chunks,
        system_prompt=system_prompt,
    )
    answer_type = _select_answer_type(intent, preferred_answer_type)
    diagnostics.update(
        {
            "low_confidence": False,
            "fallback_used": None if settings.effective_gemini_api_key else "local_rag",
            "route": "textbook_rag",
            "grounding": "book",
        }
    )
    diagnostics["confidence_components"]["final_confidence"] = round(float(confidence), 4)
    return {
        "answer": answer,
        "answer_type": answer_type,
        "route": "textbook_rag",
        "grounding": "book",
        "answer_scope": answer_scope,
        "blocks": _build_answer_blocks(
            answer,
            chunks,
            answer_type=answer_type,
            preferred_answer_type=preferred_answer_type,
            page_numbers=page_numbers,
            diagnostics=diagnostics,
        ),
        "sources": chunks,
        "source_blocks": _source_blocks(chunks),
        "page_numbers": page_numbers,
        "confidence": round(float(confidence), 4),
        "diagnostics": diagnostics,
        "suggested_next_action": "جرّب سؤالاً تدريبياً مرتبطاً بالمصدر." if chunks else "أعد صياغة السؤال أو حدد الدرس.",
    }


async def update_message_feedback(db: AsyncSession, message_id: int, user_id: int, feedback: str) -> ChatMessage:
    """Attach feedback to a message in a user's session."""
    result = await db.execute(
        select(ChatMessage)
        .options(selectinload(ChatMessage.session))
        .where(ChatMessage.id == message_id)
    )
    message = result.scalars().first()
    if message is None or message.session.user_id != user_id:
        raise HTTPException(status_code=404, detail="Message not found")
    message.feedback = feedback
    await db.commit()
    await db.refresh(message)
    return message


async def delete_session(db: AsyncSession, session_id: int, user_id: int) -> None:
    """Delete a chat session owned by the current user."""
    session = await get_owned_session(db, session_id, user_id)
    await db.delete(session)
    await db.commit()
