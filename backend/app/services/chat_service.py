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

from app.core.config import BACKEND_DIR, PROJECT_DIR, settings
from app.models.chat import ChatMessage, ChatSession
from app.rag.answer_verifier import verify_answer
from app.rag.arabic_normalizer import normalize_arabic
from app.rag.book_knowledge import BookKnowledgeAnswer, answer_from_book_knowledge
from app.rag.chunk_validator import validate_chunks
from app.services import ai_service
from app.services.chemistry_rules import answer_metal_dilute_acid_reaction, detect_metal_and_acid
from app.services.query_router import route_direct_answer
from app.services.rag import (
    RetrievedChunk,
    clean_query,
    format_context,
    lexical_relevance_score,
    rewrite_query,
)
from app.services.safety_rules import answer_safety_rule, is_acid_to_water_safety_question
from app.services.semantic_rag import semantic_retrieve_context
from app.services.source_router import route_source

logger = logging.getLogger(__name__)

_QUESTION_PASSAGE_HINTS = ("؟", "السؤال", "اختر", "ضع اشارة", "المطلوب", "احسب", "اعط تفسير")
_LOW_VALUE_PASSAGE_HINTS = ("اهداف", "اﻫﺪاف", "الكلمات المفتاحية", "اﻟﻜﻠﻤﺎت", "نشاط", "ﻧﺸﺎط")
_PASSAGE_SPLIT_RE = re.compile(r"(?<=[.؟!])\s+")

# Minimum confidence required before the chat layer is allowed to present an
# answer as grounded in textbook/solutions context. The semantic retriever now
# calibrates scores after fusion, so these thresholds can be stricter than the
# old hash-embedding-only fallback.
_MIN_BOOK_GROUNDED_CONFIDENCE = 0.45
_INTENT_BOOK_GROUNDED_THRESHOLDS = {
    "definition_lookup": 0.55,
    "property_lookup": 0.52,
    "formula_lookup": 0.50,
    "equation_lookup": 0.48,
    "reaction_query": 0.48,
    "table_lookup": 0.48,
    "book_grounded": 0.45,
    "exercise_lookup": 0.45,
    "exercise_solving": 0.45,
    "safety_question": 0.45,
    "general": 0.45,
}

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

_DEFINITION_TRIGGERS = ("ما هي", "ما هو", "ماهي", "ماهو", "عرف", "تعريف", "معنى")
_BOOK_GROUNDED_TRIGGERS = ("من الكتاب", "في الكتاب", "حسب الكتاب", "بحسب الكتاب", "من كتاب")
_FORMULA_TRIGGERS = ("صيغة", "الصيغة", "رمز", "الرمز", "formula")
_EQUATION_TRIGGERS = ("معادلة", "المعادلة", "وازن", "موزونة", "اكتب المعادلة")
_REACTION_TRIGGERS = ("تفاعل", "يتفاعل", "تتفاعل", "مع حمض", "مع الماء", "ناتج", "الناتج")
_TABLE_TRIGGERS = ("جدول", "الجدول", "سلسلة", "السلسلة")
_SAFETY_TRIGGERS = (
    "نضيف الحمض الى الماء",
    "اضف الحمض الى الماء",
    "وليس العكس",
    "لماذا نضيف الحمض",
    "الماء الى الحمض",
    "احتياطات",
    "السلامه",
)
_VALID_ANSWER_TYPES = {"auto", "text", "image", "audio", "video", "mixed"}
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
_CHEMISTRY_DICTIONARY_PATH = BACKEND_DIR / "app" / "rag" / "data" / "chemistry_entities.json"
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

    if is_acid_to_water_safety_question(question):
        return {
            "intent": "safety_question",
            "answer_style": "direct",
            "route": "safety_rule",
            **entity_payload,
        }

    if any(term in normalized for term in ("لون", "ورقه عباد", "عباد الشمس", "تلون")):
        return {"intent": "property_lookup", "answer_style": "direct", "route": "dictionary_first", **entity_payload}

    base_intent = _classify_intent(question)
    if base_intent in {"formula_lookup", "equation_lookup", "reaction_query", "table_lookup"}:
        return {"intent": base_intent, "answer_style": "direct" if entity else "normal", "route": "dictionary_first", **entity_payload}

    if (
        any(trigger in normalized for trigger in ("ما هي", "ما هو", "ماهي", "ماهو", "عرف", "تعريف"))
        or "اشرح معني" in normalized
        or "اشرح معنى" in normalized
    ):
        return {"intent": "definition_lookup", "answer_style": "direct", "route": "dictionary_first", **entity_payload}

    route = "math_solver" if base_intent == "exercise_solving" else "rag"
    return {"intent": base_intent, "answer_style": "normal", "route": route, **entity_payload}


_FOLLOWUP_REPHRASE_TRIGGERS = (
    "اشرح بطريقة اخرى",
    "اشرح بطريقه اخرى",
    "اشرح بطريقة أبسط",
    "اشرح بطريقه ابسط",
    "اشرح ببساطة",
    "اشرح ببساطه",
    "لم افهم",
    "لم أفهم",
    "اعطني مثالا ابسط",
    "اعطني مثال ابسط",
    "أعطني مثالاً أبسط",
    "explain this differently",
    "try differently",
    "simpler example",
    "simple example",
    "rephrase",
)


def _is_followup_rephrase(question: str, action: str | None = None) -> bool:
    normalized = _normalize_intent_text(question)
    action_normalized = (action or "").strip().lower()
    if action_normalized in {"rephrase_previous", "try_differently", "simplify_previous"}:
        return True
    return any(_normalize_intent_text(trigger) in normalized for trigger in _FOLLOWUP_REPHRASE_TRIGGERS)


def _classify_intent(question: str) -> str:
    """Classify the user's intent to guide retrieval behaviour.

    Returns retrieval intents such as definition_lookup, formula_lookup,
    equation_lookup, reaction_query, table_lookup, book_grounded, or general.
    """
    normalized = question.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا")
    normalized_lower = normalized.lower()

    normalized_for_property = _normalize_intent_text(question)
    if is_acid_to_water_safety_question(question) or (
        "حمض" in normalized_for_property
        and "ماء" in normalized_for_property
        and any(trigger in normalized_for_property for trigger in _SAFETY_TRIGGERS)
    ):
        return "safety_question"

    if "تركيز" in normalized_for_property and any(
        trigger in normalized_for_property for trigger in ("احسب", "حل", "مساله", "تمرين", "اوجد", "جد")
    ):
        return "exercise_solving"

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


def _confidence_threshold_for_intent(intent: str) -> float:
    return max(_MIN_BOOK_GROUNDED_CONFIDENCE, _INTENT_BOOK_GROUNDED_THRESHOLDS.get(intent, _MIN_BOOK_GROUNDED_CONFIDENCE))


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


def _append_audio_unavailable_if_requested(
    blocks: list[dict],
    *,
    preferred_answer_type: str,
    diagnostics: dict,
) -> None:
    if (preferred_answer_type or "").strip().lower() != "audio":
        return
    diagnostics["audio_requested_but_tts_unavailable"] = True
    blocks.append(
        {
            "type": "audio",
            "content": "Audio generation is still processing.",
            "url": None,
            "page": None,
            "image_url": None,
            "metadata": {"tts_available": False},
        }
    )


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
    validations = validate_chunks(
        question,
        chunks,
        entity=entity.entity if entity else None,
        intent=intent,
    )
    return {
        "original_query": question,
        "normalized_query": cleaned,
        "normalized_question": normalize_arabic(question),
        "intent": intent,
        "entity": entity.entity if entity else None,
        "normalized_entity": entity.normalized_entity if entity else None,
        "rewritten_query": rewritten,
        "retrieved_chunks": [
            {
                "chunk_id": validation.chunk_id,
                "page": validation.page,
                "chunk_type": chunk.content_type,
                "score": validation.score,
                "valid_for_answer": validation.valid_for_answer,
                "rejection_reason": validation.rejection_reason,
                "preview": validation.preview,
                "content_preview": validation.preview,
            }
            for chunk, validation in zip(chunks, validations, strict=False)
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
    _append_audio_unavailable_if_requested(
        text_blocks,
        preferred_answer_type=preferred_answer_type,
        diagnostics=diagnostics,
    )

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
            "route": "dictionary_first",
            "grounding": "approved_dictionary",
            "answer_scope": diagnostics.get("answer_scope", "auto"),
            "rag_search_skipped": True,
        }
    )
    _append_audio_unavailable_if_requested(
        blocks,
        preferred_answer_type=preferred_answer_type,
        diagnostics=diagnostics,
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
            "rag_search_skipped": not bool(chunks),
        }
    )
    _append_audio_unavailable_if_requested(
        blocks,
        preferred_answer_type=preferred_answer_type,
        diagnostics=diagnostics,
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


def _litmus_rule_response(
    *,
    question: str,
    preferred_answer_type: str,
    answer_scope: str,
    diagnostics: dict,
) -> dict | None:
    normalized = _normalize_intent_text(question)
    if not ("عباد الشمس" in normalized or "ورقه عباد" in normalized or "ورقة عباد" in question):
        return None
    acidic = any(term in normalized for term in ("حمضي", "حمضيه", "حموض", "حمض", "احماض"))
    basic = any(term in normalized for term in ("اساسي", "اساسيه", "اسس", "قاعد", "قلوي"))
    if not acidic and not basic:
        return None
    if acidic:
        answer = "تتلون ورقة عباد الشمس باللون الأحمر في المحاليل الحمضية."
        entity_name = "المحاليل الحمضية"
        pages = [13]
    else:
        answer = "تتلون ورقة عباد الشمس باللون الأزرق في المحاليل الأساسية."
        entity_name = "المحاليل الأساسية"
        pages = [23]
    answer_type = _select_answer_type("property_lookup", preferred_answer_type)
    diagnostics.update(
        {
            "intent": "property_lookup",
            "entity": entity_name,
            "route": "chemistry_rule",
            "grounding": "book_knowledge",
            "answer_scope": answer_scope,
            "rule_engine": "litmus_color",
            "retrieved_chunks": [],
            "selected_context": [],
            "confidence": 0.95,
            "rag_search_skipped": True,
        }
    )
    return {
        "answer": answer,
        "answer_type": answer_type,
        "route": "chemistry_rule",
        "grounding": "book_knowledge",
        "answer_scope": answer_scope,
        "blocks": _build_answer_blocks(
            answer,
            [],
            answer_type=answer_type,
            preferred_answer_type=preferred_answer_type,
            page_numbers=pages,
            diagnostics=diagnostics,
        ),
        "sources": [],
        "source_blocks": [
            {
                "book_id": _SOURCE_SLUG,
                "page": page,
                "chunk_id": 0,
                "chunk_type": "chemistry_rule",
                "score": 0.95,
            }
            for page in pages
        ],
        "page_numbers": pages,
        "confidence": 0.95,
        "diagnostics": diagnostics,
        "suggested_next_action": "يمكنك أن تسأل عن تجربة التمييز بين المحاليل الحمضية والأساسية.",
    }


def _safety_rule_response(
    *,
    question: str,
    preferred_answer_type: str,
    answer_scope: str,
    diagnostics: dict,
) -> dict | None:
    safety_answer = answer_safety_rule(question)
    if not safety_answer:
        return None

    answer_type = _select_answer_type("safety_question", preferred_answer_type)
    diagnostics.update(
        _retrieval_diagnostics(
            question=question,
            intent="safety_question",
            entity=None,
            chunks=[],
            confidence=safety_answer.confidence,
        )
    )
    diagnostics.update(
        {
            "intent": safety_answer.intent,
            "route": safety_answer.route,
            "grounding": "safety_rule",
            "answer_scope": answer_scope,
            "rule_engine": "acid_to_water_safety",
            "matched_terms": safety_answer.matched_terms,
            "retrieved_chunks": [],
            "selected_context": [],
            "selected_source_pages": safety_answer.page_numbers,
            "rag_search_skipped": True,
            "fallback_used": "local_router",
            "gemini_available": bool(settings.effective_gemini_api_key),
            "gemini_error": None,
            "gemini_skipped_reason": "deterministic_safety_rule",
        }
    )
    source_blocks = [
        {
            "book_id": _SOURCE_SLUG,
            "page": page,
            "chunk_id": 0,
            "chunk_type": "safety_rule",
            "score": safety_answer.confidence,
        }
        for page in safety_answer.page_numbers
    ]
    blocks = _build_answer_blocks(
        safety_answer.answer,
        [],
        answer_type=answer_type,
        preferred_answer_type=preferred_answer_type,
        page_numbers=safety_answer.page_numbers,
        diagnostics=diagnostics,
    )
    return {
        "answer": safety_answer.answer,
        "answer_type": answer_type,
        "route": safety_answer.route,
        "grounding": "safety_rule",
        "answer_scope": answer_scope,
        "blocks": blocks,
        "sources": [],
        "source_blocks": source_blocks,
        "page_numbers": safety_answer.page_numbers,
        "confidence": round(float(safety_answer.confidence), 4),
        "diagnostics": diagnostics,
        "suggested_next_action": safety_answer.suggested_next_action,
    }


def _book_knowledge_response(
    *,
    item: BookKnowledgeAnswer,
    preferred_answer_type: str,
    answer_scope: str,
    diagnostics: dict,
) -> dict:
    answer_type = _select_answer_type(item.intent, preferred_answer_type)
    diagnostics.update(
        {
            "intent": item.intent,
            "route": "book_knowledge",
            "grounding": "book",
            "answer_scope": answer_scope,
            "book_knowledge_key": item.key,
            "retrieved_chunks": [],
            "selected_context": [],
            "confidence": item.confidence,
            "rag_search_skipped": True,
        }
    )
    return {
        "answer": item.answer,
        "answer_type": answer_type,
        "route": "book_knowledge",
        "grounding": "book",
        "answer_scope": answer_scope,
        "blocks": _build_answer_blocks(
            item.answer,
            [],
            answer_type=answer_type,
            preferred_answer_type=preferred_answer_type,
            page_numbers=item.page_numbers,
            diagnostics=diagnostics,
        ),
        "sources": [],
        "source_blocks": [
            {
                "book_id": _SOURCE_SLUG,
                "page": page,
                "chunk_id": 0,
                "chunk_type": item.source_type,
                "score": item.confidence,
            }
            for page in item.page_numbers
        ],
        "page_numbers": item.page_numbers,
        "confidence": round(float(item.confidence), 4),
        "diagnostics": diagnostics,
        "suggested_next_action": "يمكنك أن تطلب مثالاً مشابهاً أو سؤالاً تدريبياً.",
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


def _previous_page_numbers(previous_sources: list[dict] | None, previous_selected_chunks: list[dict] | None) -> list[int]:
    pages: set[int] = set()
    for item in (previous_sources or []) + (previous_selected_chunks or []):
        page = item.get("page") if isinstance(item, dict) else None
        if page is None:
            page = item.get("page_number") if isinstance(item, dict) else None
        try:
            if page is not None:
                pages.add(int(page))
        except (TypeError, ValueError):
            continue
    return sorted(pages)


def _previous_source_blocks(previous_sources: list[dict] | None, previous_selected_chunks: list[dict] | None) -> list[dict]:
    blocks: list[dict] = []
    for item in (previous_selected_chunks or []) + (previous_sources or []):
        if not isinstance(item, dict):
            continue
        chunk_id = item.get("chunk_id") or item.get("id") or 0
        page = item.get("page") if item.get("page") is not None else item.get("page_number")
        score = item.get("score") if item.get("score") is not None else item.get("similarity_score")
        try:
            score_value = round(float(score), 4) if score is not None else 0.0
        except (TypeError, ValueError):
            score_value = 0.0
        blocks.append(
            {
                "book_id": item.get("book_id") or item.get("source") or _SOURCE_SLUG,
                "page": page,
                "chunk_id": chunk_id,
                "chunk_type": item.get("chunk_type") or item.get("content_type") or "previous_context",
                "score": score_value,
            }
        )
    deduped: list[dict] = []
    seen: set[tuple[object, object]] = set()
    for block in blocks:
        key = (block["chunk_id"], block["page"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(block)
    return deduped


def _simplify_previous_answer(previous_answer: str, previous_question: str | None = None) -> str:
    normalized_previous = _normalize_intent_text(previous_answer)
    normalized_question = _normalize_intent_text(previous_question or "")
    if "ايونات الهدروجين" in normalized_previous or "h+" in normalized_previous or "حموض" in normalized_question:
        return (
            "ببساطة: الحمض مثل مادة عندما تذوب في الماء تترك أيونات الهدروجين H⁺.\n\n"
            "مثال: حمض كلور الماء HCl عندما يوجد في الماء يعطي أيونات H⁺، "
            "ولهذا نعدّه حمضاً."
        )
    if "ايونات الهدروكسيد" in normalized_previous or "oh" in normalized_previous or "اسس" in normalized_question:
        return (
            "ببساطة: الأساس مادة عندما تذوب في الماء تترك أيونات الهدروكسيد OH⁻.\n\n"
            "مثال: هيدروكسيد الصوديوم NaOH يعطي OH⁻ في الماء، لذلك يعد من الأسس."
        )
    if "h2o" in normalized_previous or "ماء" in normalized_question:
        return (
            "ببساطة: الماء مركب وليس عنصراً واحداً. صيغته H₂O، "
            "أي أن كل جزيء ماء يتكون من ذرتي هيدروجين وذرة أكسجين."
        )
    cleaned = _clean_display_arabic(previous_answer)
    return f"بصياغة أبسط:\n{cleaned}"


def _followup_rephrase_response(
    *,
    question: str,
    previous_question: str | None,
    previous_answer: str | None,
    previous_sources: list[dict] | None,
    previous_selected_chunks: list[dict] | None,
    answer_scope: str,
    preferred_answer_type: str,
    conversation_id: str | None,
    parent_message_id: str | None,
    diagnostics: dict,
) -> dict:
    if not previous_answer:
        answer = (
            "أحتاج إلى السؤال أو الإجابة السابقة حتى أشرحها بطريقة أبسط. "
            "أرسل السؤال السابق أو اسأل من جديد."
        )
        diagnostics.update({"route": "followup_rephrase", "missing_previous_context": True})
        return {
            "answer": answer,
            "answer_type": "clarification",
            "route": "followup_rephrase",
            "grounding": "previous_context",
            "answer_scope": answer_scope,
            "blocks": [{"type": "clarification", "content": answer, "page": None, "image_url": None, "metadata": {}}],
            "sources": [],
            "source_blocks": [],
            "page_numbers": [],
            "confidence": 0.0,
            "diagnostics": diagnostics,
            "suggested_next_action": "اسأل السؤال الأصلي مرة أخرى ثم اضغط Try differently.",
        }

    answer = _simplify_previous_answer(previous_answer, previous_question)
    page_numbers = _previous_page_numbers(previous_sources, previous_selected_chunks)
    source_blocks = _previous_source_blocks(previous_sources, previous_selected_chunks)
    answer_type = _select_answer_type("followup_rephrase", preferred_answer_type)
    if answer_type == "auto":
        answer_type = "text"
    diagnostics.update(
        {
            "original_question": question,
            "resolved_question": previous_question or question,
            "is_followup": True,
            "conversation_id": conversation_id,
            "parent_message_id": parent_message_id,
            "answer_scope": answer_scope,
            "preferred_answer_type": preferred_answer_type,
            "intent": "followup_rephrase",
            "entity": None,
            "route": "followup_rephrase",
            "grounding": "previous_context",
            "retrieved_chunks": [],
            "selected_context": previous_selected_chunks or previous_sources or [],
            "confidence": 0.86,
            "rag_search_skipped": True,
        }
    )
    return {
        "answer": answer,
        "answer_type": answer_type,
        "route": "followup_rephrase",
        "grounding": "previous_context",
        "answer_scope": answer_scope,
        "blocks": _build_answer_blocks(
            answer,
            [],
            answer_type=answer_type,
            preferred_answer_type=preferred_answer_type,
            page_numbers=page_numbers,
            diagnostics=diagnostics,
        ),
        "sources": [],
        "source_blocks": source_blocks,
        "page_numbers": page_numbers,
        "confidence": 0.86,
        "diagnostics": diagnostics,
        "suggested_next_action": "يمكنك طلب مثال آخر أو سؤال تدريبي على نفس الفكرة.",
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

    if preferred_answer_type == "audio":
        if diagnostics is not None:
            diagnostics["audio_requested_but_tts_unavailable"] = True
        blocks.append(
            {
                "type": "audio",
                "content": "Audio generation is still processing.",
                "url": None,
                "page": None,
                "image_url": None,
                "metadata": {"tts_available": False},
            }
        )

    return blocks


def _finalize_answer(result: dict, question: str) -> dict:
    diagnostics = result.setdefault("diagnostics", {})
    diagnostics.setdefault("original_question", question)
    diagnostics.setdefault("normalized_question", normalize_arabic(question))
    diagnostics.setdefault("route", result.get("route"))
    diagnostics.setdefault("grounding", result.get("grounding"))
    diagnostics.setdefault("confidence", result.get("confidence"))
    verification = verify_answer(question, result.get("answer", ""))
    diagnostics["verification"] = verification.as_dict()
    if not verification.passed:
        diagnostics["verification_failed"] = True
    return result


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

_ANSWER_QUALITY_PROMPT_RULES = (
    "قواعد جودة الإجابة:\n"
    "- لا تكتب عنواناً فارغاً أو عنواناً لا يتبعه محتوى حقيقي.\n"
    "- إذا كان السؤال عن مفهوم بسيط (مثل تعريف عنصر أو رمز كيميائي أو صيغة مركب) والمقاطع المسترجعة لا تحتوي على تعريف مباشر لهذا المفهوم، أجب عن السؤال مباشرة من معلوماتك الكيميائية العامة بأسلوب معلم كيمياء ودود. لا تجبر المقاطع غير المرتبطة على أن تكون الإجابة.\n"
    "- بعد الإجابة المباشرة، إن أمكن اربط إجابتك بالمواضيع والتجارب الواردة في مقاطع الكتاب المتاحة واذكر أرقام الصفحات المرتبطة (مثال: 'رمز غاز ثاني أكسيد الكربون هو CO₂. وفي كتابك يذكر هذا الغاز كناتج في تفاعل احتراق البوتان في الصفحة 79').\n"
    "- لا تخترع أرقام صفحات غير موجودة في المقاطع المتاحة.\n"
    "- إذا كانت المقاطع تحتوي على معلومات عن مفهوم مختلف (مثل: سألت عن الماء فجاءت مقاطع عن الحموض) فلا تجب عن المفهوم الخاطئ — أجب عن السؤال الأصلي مباشرة.\n"
    "Answer quality rules: never create empty headings. If the question asks about a basic chemistry concept (element, symbol, formula) and the retrieved passages do NOT contain a direct definition for it, answer from your general chemistry knowledge directly. Do NOT force unrelated passages to be the answer. If passages discuss a different topic than what was asked, answer the original question instead. Do not invent page numbers.\n"
)

_SYSTEM_PROMPT_WITH_CONTEXT = (
    "أنت مدرس كيمياء للصف التاسع. أجب بالاعتماد على المقاطع التالية من الكتاب كمصدرك المرجعي الرئيسي.\n"
    "التعليمات:\n"
    "1. استخدم المعلومات الموجودة في المقاطع لربط الإجابة بالمنهج الدراسي والصفحات المذكورة. اذكر رقم الصفحة لكل معلومة مستقاة من الكتاب بالشكل: (صفحة XX).\n"
    "2. إذا كان السؤال عن مفهوم أساسي أو عام في الكيمياء (مثل تعريف عنصر، رمز كيميائي، صيغة مركب، إلخ) ولم يكن مشروحاً بالتفصيل في المقاطع، استخدم معلوماتك الكيميائية العامة لتقديم إجابة واضحة وصحيحة ومبسطة كمعلم كيمياء للصف التاسع، ثم اربطها بالمواضيع أو التجارب الواردة في مقاطع الكتاب المتاحة واذكر صفحاتها.\n"
    "3. لا تخترع أرقام صفحات أو معلومات غير موجودة في المقاطع.\n"
    "4. رتب إجابتك: التعريف أولاً، ثم التفاصيل، ثم الأمثلة.\n"
    "5. تنبيه هام جداً: لا تستخدم صيغة LaTeX أو لغة الرياضيات (مثل $...$ أو $$...$$ أو \\text) لكتابة الصيغ الكيميائية أو المعادلات. اكتب الصيغ الكيميائية دائماً كنص عادي باستخدام الرموز الكيميائية والأرقام السفلية (Subscripts) (مثل CO₂، H₂O، H₂SO₄)، واكتب المعادلات الكيميائية على سطر منفرد جديد كرموز نصية عادية مع السهم -> أو → (مثل: 2H2 + O2 -> 2H2O).\n"
    "CRITICAL: Never use LaTeX or math mode ($...$, $$...$$, \\text) for chemistry formulas or equations. Render formulas as normal text with subscript numbers (e.g., CO₂, H₂O, H₂SO₄) and equations as clean plain text on a new line (e.g., 2H2 + O2 -> 2H2O).\n\n"
    f"{_ANSWER_QUALITY_PROMPT_RULES}\n"
    "المقاطع:\n{context}"
)

_SYSTEM_PROMPT_NO_CONTEXT = (
    "أنت مدرس كيمياء للصف التاسع. أجب عن أسئلة الطلاب بأسلوب تعليمي ودود وواضح باللغة العربية.\n"
    "إذا كان السؤال خارج نطاق المنهج الدراسي أو لم تجد له مصدراً في الكتاب، أجب عنه مباشرة مستعيناً بمعلوماتك الكيميائية العامة بأسلوب مبسط ومناسب لطالب في الصف التاسع.\n"
    "تنبيه هام جداً: لا تستخدم صيغة LaTeX أو لغة الرياضيات (مثل $...$ أو $$...$$ أو \\text) لكتابة الصيغ الكيميائية أو المعادلات. اكتب الصيغ الكيميائية دائماً كنص عادي باستخدام الرموز الكيميائية والأرقام السفلية (Subscripts) (مثل CO₂، H₂O، H₂SO₄)، واكتب المعادلات الكيميائية على سطر منفرد جديد كرموز نصية عادية مع السهم -> أو → (مثل: 2H2 + O2 -> 2H2O).\n"
    "CRITICAL: Never use LaTeX or math mode ($...$, $$...$$, \\text) for chemistry formulas or equations. Render formulas as normal text with subscript numbers (e.g., CO₂, H₂O, H₂SO₄) and equations as clean plain text on a new line (e.g., 2H2 + O2 -> 2H2O).\n\n"
    f"{_ANSWER_QUALITY_PROMPT_RULES}"
)

_SYSTEM_PROMPT_ASK_WITH_CONTEXT = (
    "أنت مدرس كيمياء للصف التاسع. أجب بالاعتماد على المقاطع التالية من الكتاب كمصدرك المرجعي الرئيسي.\n"
    "التعليمات:\n"
    "1. استخدم المعلومات الموجودة في المقاطع لربط الإجابة بالمنهج الدراسي والصفحات المذكورة. اذكر رقم الصفحة لكل معلومة مستقاة من الكتاب بالشكل: (صفحة XX).\n"
    "2. إذا كان السؤال عن مفهوم أساسي أو عام في الكيمياء (مثل تعريف عنصر، رمز كيميائي، صيغة مركب، إلخ) ولم يكن مشروحاً بالتفصيل في المقاطع، استخدم معلوماتك الكيميائية العامة لتقديم إجابة واضحة وصحيحة ومبسطة كمعلم كيمياء للصف التاسع، ثم اربطها بالمواضيع أو التجارب الواردة في مقاطع الكتاب المتاحة واذكر صفحاتها.\n"
    "3. لا تخترع أرقام صفحات أو معلومات غير موجودة في المقاطع.\n"
    "4. تنبيه هام جداً: لا تستخدم صيغة LaTeX أو لغة الرياضيات (مثل $...$ أو $$...$$ أو \\text) لكتابة الصيغ الكيميائية أو المعادلات. اكتب الصيغ الكيميائية دائماً كنص عادي باستخدام الرموز الكيميائية والأرقام السفلية (Subscripts) (مثل CO₂، H₂O، H₂SO₄)، واكتب المعادلات الكيميائية على سطر منفرد جديد كرموز نصية عادية مع السهم -> أو → (مثل: 2H2 + O2 -> 2H2O).\n"
    "CRITICAL: Never use LaTeX or math mode ($...$, $$...$$, \\text) for chemistry formulas or equations. Render formulas as normal text with subscript numbers (e.g., CO₂, H₂O, H₂SO₄) and equations as clean plain text on a new line (e.g., 2H2 + O2 -> 2H2O).\n\n"
    f"{_ANSWER_QUALITY_PROMPT_RULES}\n"
    "المقاطع:\n{context}"
)

_SYSTEM_PROMPT_ASK_NO_CONTEXT = (
    "أنت مدرس كيمياء للصف التاسع. أجب عن أسئلة الطلاب بأسلوب تعليمي ودود وواضح باللغة العربية.\n"
    "إذا كان السؤال خارج نطاق المنهج الدراسي أو لم تجد له مصدراً في الكتاب، أجب عنه مباشرة مستعيناً بمعلوماتك الكيميائية العامة بأسلوب مبسط ومناسب لطالب في الصف التاسع.\n"
    "تنبيه هام جداً: لا تستخدم صيغة LaTeX أو لغة الرياضيات (مثل $...$ أو $$...$$ أو \\text) لكتابة الصيغ الكيميائية أو المعادلات. اكتب الصيغ الكيميائية دائماً كنص عادي باستخدام الرموز الكيميائية والأرقام السفلية (Subscripts) (مثل CO₂، H₂O، H₂SO₄)، واكتب المعادلات الكيميائية على سطر منفرد جديد كرموز نصية عادية مع السهم -> أو → (مثل: 2H2 + O2 -> 2H2O).\n"
    "CRITICAL: Never use LaTeX or math mode ($...$, $$...$$, \\text) for chemistry formulas or equations. Render formulas as normal text with subscript numbers (e.g., CO₂, H₂O, H₂SO₄) and equations as clean plain text on a new line (e.g., 2H2 + O2 -> 2H2O).\n\n"
    f"{_ANSWER_QUALITY_PROMPT_RULES}"
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


def _is_acid_to_water_safety_question(question: str) -> bool:
    return is_acid_to_water_safety_question(question)


def _acid_to_water_safety_answer_from_chunks(chunks: list[RetrievedChunk]) -> str | None:
    combined = "\n".join(chunk.content for chunk in chunks)
    normalized = combined.replace("إ", "ا").replace("أ", "ا").replace("آ", "ا").replace("ة", "ه")
    if "حمض" not in normalized or "ماء" not in normalized:
        return None
    if "اضف الحمض الى الماء" not in normalized and "تحذير" not in normalized:
        return None

    pages = sorted({chunk.page_number for chunk in chunks if chunk.page_number is not None})
    selected_pages = "، ".join(str(page) for page in pages if page in {7}) or "، ".join(str(page) for page in pages)
    return (
        "من الكتاب:\n"
        "يرد التحذير: أضف الحمض إلى الماء، وليس العكس.\n\n"
        "السبب:\n"
        "- تمديد الحمض بالماء يحرر حرارة.\n"
        "- عند إضافة الماء إلى الحمض المركز قد ترتفع الحرارة بسرعة ويتطاير الحمض خارج الوعاء.\n"
        "- لذلك نضيف الحمض تدريجياً إلى كمية أكبر من الماء مع التحريك لتتوزع الحرارة بأمان.\n\n"
        f"المصدر: صفحة {selected_pages}."
    )


def _local_rag_answer(question: str, chunks: list[RetrievedChunk], reason: str | None = None) -> str:
    """Build a useful source-backed fallback when no Gemini key is configured."""
    intro = "إجابة مبنية على مقاطع الكتاب المتاحة."
    if not chunks:
        return (
            f"{intro}\n\n"
            "لم أجد مقاطع كافية من الكتاب للإجابة عن السؤال بدقة."
        )

    if _is_acid_to_water_safety_question(question):
        answer = _acid_to_water_safety_answer_from_chunks(chunks)
        if answer:
            return answer

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
    diagnostics: dict | None = None,
) -> str:
    if not settings.effective_gemini_api_key:
        if diagnostics is not None:
            diagnostics.update(
                {
                    "gemini_available": False,
                    "gemini_error": "API_KEY_MISSING",
                    "fallback_used": "local_router",
                }
            )
        return _local_rag_answer(question, chunks)

    try:
        answer = await ai_service.get_ai_response(messages, system_prompt=system_prompt, raise_on_error=True)
        if answer.strip():
            if diagnostics is not None:
                diagnostics.update({"gemini_available": True, "gemini_error": None, "fallback_used": None})
            return answer
        if diagnostics is not None:
            diagnostics.update(
                {
                    "gemini_available": False,
                    "gemini_error": "EMPTY_RESPONSE",
                    "fallback_used": "local_router",
                }
            )
        return _local_rag_answer(
            question,
            chunks,
            reason="عاد Gemini برد فارغ حالياً، لذلك أعرض لك إجابة محلية من مصادر الكتاب.",
        )
    except ai_service.AIQuotaExceededError:
        logger.info("Gemini quota exceeded; using local RAG fallback.")
        if diagnostics is not None:
            diagnostics.update(
                {
                    "gemini_available": False,
                    "gemini_error": "RESOURCE_EXHAUSTED",
                    "fallback_used": "local_router",
                }
            )
        return _local_rag_answer(
            question,
            chunks,
            reason="local_rag",
        )
    except ai_service.AIServiceError:
        logger.info("Gemini service failed; using local RAG fallback.")
        if diagnostics is not None:
            diagnostics.update(
                {
                    "gemini_available": False,
                    "gemini_error": "SERVICE_UNAVAILABLE",
                    "fallback_used": "local_router",
                }
            )
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

    semantic_result = await semantic_retrieve_context(
        db,
        content,
        user_id=user_id,
        top_k=6,
        intent=intent,
    )
    chunks = semantic_result.chunks
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


async def _context_from_parent_message(
    db: AsyncSession | None,
    user_id: int,
    parent_message_id: str | None,
) -> tuple[str | None, str | None]:
    if db is None or not parent_message_id:
        return None, None
    try:
        message_id = int(parent_message_id)
    except (TypeError, ValueError):
        return None, None

    result = await db.execute(
        select(ChatMessage)
        .options(selectinload(ChatMessage.session))
        .where(ChatMessage.id == message_id)
    )
    parent = result.scalars().first()
    if parent is None or parent.session.user_id != user_id:
        return None, None

    previous_answer = parent.content if parent.role == "assistant" else None
    previous_question = None
    if parent.role == "assistant":
        previous_result = await db.execute(
            select(ChatMessage)
            .where(
                ChatMessage.session_id == parent.session_id,
                ChatMessage.role == "user",
                ChatMessage.created_at <= parent.created_at,
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        previous_user_message = previous_result.scalars().first()
        previous_question = previous_user_message.content if previous_user_message else None
    else:
        previous_question = parent.content
    return previous_question, previous_answer


async def ask_question(
    db: AsyncSession,
    user_id: int,
    question: str,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    source_types: list[str] | None = None,
    preferred_answer_type: str = "text",
    answer_scope: str = "auto",
    conversation_id: str | None = None,
    parent_message_id: str | None = None,
    teaching_style: str | None = None,
    action: str | None = None,
    previous_question: str | None = None,
    previous_answer: str | None = None,
    previous_sources: list[dict] | None = None,
    previous_selected_chunks: list[dict] | None = None,
) -> dict:
    """Answer a one-off question with RAG sources."""
    answer_scope = _normalize_answer_scope(answer_scope)

    if _is_followup_rephrase(question, action=action):
        parent_question, parent_answer = await _context_from_parent_message(db, user_id, parent_message_id)
        diagnostics = {
            "original_query": question,
            "original_question": question,
            "normalized_question": normalize_arabic(question),
            "resolved_question": previous_question or parent_question or question,
            "is_followup": True,
            "conversation_id": conversation_id,
            "parent_message_id": parent_message_id,
            "answer_scope": answer_scope,
            "preferred_answer_type": preferred_answer_type,
            "teaching_style": teaching_style,
            "action": action,
            "intent": "followup_rephrase",
            "entity": None,
            "gemini_available": bool(settings.effective_gemini_api_key),
        }
        return _finalize_answer(_followup_rephrase_response(
            question=question,
            previous_question=previous_question or parent_question,
            previous_answer=previous_answer or parent_answer,
            previous_sources=previous_sources or [],
            previous_selected_chunks=previous_selected_chunks or [],
            answer_scope=answer_scope,
            preferred_answer_type=preferred_answer_type,
            conversation_id=conversation_id,
            parent_message_id=parent_message_id,
            diagnostics=diagnostics,
        ), question)

    classification = _classify_question(question)
    intent = classification["intent"]
    entity = _definition_entity_for_question(question)
    explicit_book = _explicit_book_requested(question)
    dictionary_entry = _dictionary_entry_for_question(question, intent=intent)
    metal, acid = detect_metal_and_acid(question)
    diagnostics: dict = {
        "original_query": question,
        "original_question": question,
        "resolved_question": question,
        "is_followup": False,
        "conversation_id": conversation_id,
        "parent_message_id": parent_message_id,
        "normalized_query": clean_query(question),
        "normalized_question": normalize_arabic(question),
        "intent": intent,
        "entity": classification.get("entity"),
        "normalized_entity": classification.get("normalized_entity"),
        "answer_style": classification.get("answer_style"),
        "preferred_answer_type": preferred_answer_type,
        "answer_scope": answer_scope,
        "teaching_style": teaching_style,
        "action": action,
        "explicit_book_requested": explicit_book,
        "dictionary_entry_id": dictionary_entry.id if dictionary_entry else None,
        "reactants": {
            "metal": metal.symbol if metal else None,
            "acid": acid.formula if acid else None,
        },
        "gemini_available": bool(settings.effective_gemini_api_key),
    }

    safety_rule = _safety_rule_response(
        question=question,
        preferred_answer_type=preferred_answer_type,
        answer_scope=answer_scope,
        diagnostics=diagnostics,
    )
    if safety_rule:
        return _finalize_answer(safety_rule, question)

    # -----------------------------------------------------------------------
    # Exercise solving: try Solution Book RAG first (high-confidence), then
    # fall back to the deterministic math_solver rule engine.
    # -----------------------------------------------------------------------
    if intent == "exercise_solving" or classification.get("route") == "math_solver":
        # 1. Try Solution Book RAG if we have a DB session (async context)
        _solution_rag_confidence_threshold = 0.72
        _solution_rag_chunks: list = []
        try:
            _sol_rag_result = await semantic_retrieve_context(
                db,
                question,
                source_types=["solution_book"],
                top_k=4,
                intent="exercise_solving",
                document_type="solution_book",
            )
            _solution_rag_chunks = _sol_rag_result.chunks
        except Exception:
            _solution_rag_chunks = []

        _top_sol_score = max(
            (getattr(c, "similarity_score", 0) or 0 for c in _solution_rag_chunks),
            default=0,
        )
        if _solution_rag_chunks and _top_sol_score >= _solution_rag_confidence_threshold:
            # High-confidence solution book match — build answer from these chunks
            answer_type = _select_answer_type("exercise_solving", preferred_answer_type)
            _sol_context = format_context(_solution_rag_chunks)
            _sol_system_prompt = (
                _SYSTEM_PROMPT_ASK_WITH_CONTEXT.format(context=_sol_context)
                if _sol_context
                else _SYSTEM_PROMPT_ASK_NO_CONTEXT
            )
            _sol_answer = await _answer_with_rag_fallback(
                messages=[{"role": "user", "content": question}],
                question=question,
                chunks=_solution_rag_chunks,
                system_prompt=_sol_system_prompt,
                diagnostics=diagnostics,
            )
            diagnostics.update(
                {
                    "intent": "exercise_solving",
                    "route": "solution_book_rag",
                    "grounding": "solution_book",
                    "answer_scope": answer_scope,
                    "retrieved_chunks": [getattr(c, "id", None) for c in _solution_rag_chunks],
                    "solution_book_confidence": _top_sol_score,
                    "rag_search_skipped": False,
                    "fallback_used": None,
                }
            )
            return _finalize_answer(
                {
                    "answer": _sol_answer,
                    "answer_type": answer_type,
                    "route": "solution_book_rag",
                    "grounding": "solution_book",
                    "answer_scope": answer_scope,
                    "blocks": _build_answer_blocks(
                        _sol_answer,
                        _solution_rag_chunks,
                        answer_type=answer_type,
                        preferred_answer_type=preferred_answer_type,
                        diagnostics=diagnostics,
                    ),
                    "sources": _solution_rag_chunks,
                    "source_blocks": _source_blocks(_solution_rag_chunks),
                    "page_numbers": sorted({c.page_number for c in _solution_rag_chunks if c.page_number}),
                    "confidence": _top_sol_score,
                    "diagnostics": diagnostics,
                    "suggested_next_action": None,
                },
                question,
            )

        # 2. Deterministic math_solver fallback
        math_answer = route_direct_answer(question)
        if math_answer:
            answer_type = _select_answer_type(math_answer.intent, preferred_answer_type)
            diagnostics.update(
                {
                    "intent": math_answer.intent,
                    "rule_engine": "math_solver",
                    "route": math_answer.route,
                    "grounding": math_answer.grounding,
                    "answer_scope": answer_scope,
                    "extracted_values": getattr(math_answer, "extracted_values", None) or {},
                    "retrieved_chunks": [],
                    "selected_context": [],
                    "rag_search_skipped": True,
                    "fallback_used": "local_router",
                }
            )
            return _finalize_answer(
                {
                    "answer": math_answer.answer,
                    "answer_type": answer_type,
                    "route": math_answer.route,
                    "grounding": math_answer.grounding,
                    "answer_scope": answer_scope,
                    "blocks": _build_answer_blocks(
                        math_answer.answer,
                        [],
                        answer_type=answer_type,
                        preferred_answer_type=preferred_answer_type,
                        page_numbers=math_answer.page_numbers,
                        diagnostics=diagnostics,
                    ),
                    "sources": [],
                    "source_blocks": [],
                    "page_numbers": math_answer.page_numbers,
                    "confidence": math_answer.confidence,
                    "diagnostics": diagnostics,
                    "suggested_next_action": math_answer.suggested_next_action,
                },
                question,
            )

    source_route = await route_source(question, source_types)
    routed_source_types = source_route.source_types
    diagnostics["source_route"] = {
        "route": source_route.route,
        "source_types": routed_source_types,
        "reason": source_route.reason,
        "confidence": source_route.confidence,
        "matched_terms": source_route.matched_terms,
        "cache_hit": source_route.cache_hit,
    }

    simple_dictionary_intents = {"definition_lookup", "formula_lookup", "property_lookup"}

    litmus_rule = _litmus_rule_response(
        question=question,
        preferred_answer_type=preferred_answer_type,
        answer_scope=answer_scope,
        diagnostics=diagnostics,
    )
    if litmus_rule and answer_scope != "book_only":
        return _finalize_answer(litmus_rule, question)

    # Catch-all dictionary gate: if the question matches a known approved
    # dictionary entity, return the dictionary answer directly — no RAG.
    # This covers definition_lookup, formula_lookup, property_lookup AND
    # general/reaction_query intents that happen to match a known entity.
    _dictionary_eligible_intents = simple_dictionary_intents | {"general", "reaction_query"}
    if (
        dictionary_entry
        and answer_scope in {"auto", "tutor_general"}
        and not explicit_book
        and (intent in _dictionary_eligible_intents or answer_scope == "tutor_general")
    ):
        return _finalize_answer(_dictionary_response(
            entry=dictionary_entry,
            question=question,
            answer_scope=answer_scope,
            preferred_answer_type=preferred_answer_type,
            route="dictionary_first",
            grounding="approved_dictionary" if answer_scope == "auto" else "general_tutor",
            diagnostics=diagnostics,
        ), question)

    if intent == "property_lookup" and entity and answer_scope != "book_only" and not explicit_book:
        property_response = _direct_property_response(
            entity=entity,
            preferred_answer_type=preferred_answer_type,
            diagnostics=diagnostics,
        )
        if property_response:
            return _finalize_answer(property_response, question)

    reaction_answer = answer_metal_dilute_acid_reaction(question)
    if reaction_answer and answer_scope != "book_only":
        answer_type = _select_answer_type(reaction_answer.intent, preferred_answer_type)
        diagnostics.update(
            {
                "intent": reaction_answer.intent,
                "route": "chemistry_rule",
                "grounding": "book_knowledge",
                "rule_engine": "activity_series",
                "reaction_happens": reaction_answer.reaction_happens,
                "equation": reaction_answer.equation,
                "warnings": reaction_answer.warnings,
                "retrieved_chunks": [],
                "selected_context": [],
                "rag_search_skipped": True,
            }
        )
        return _finalize_answer({
            "answer": reaction_answer.answer,
            "answer_type": answer_type,
            "route": "chemistry_rule",
            "grounding": "book_knowledge",
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
        }, question)

    book_knowledge = answer_from_book_knowledge(question, intent=intent)
    if book_knowledge and answer_scope in {"auto", "book_only"}:
        return _finalize_answer(
            _book_knowledge_response(
                item=book_knowledge,
                preferred_answer_type=preferred_answer_type,
                answer_scope=answer_scope,
                diagnostics=diagnostics,
            ),
            question,
        )

    direct_answer = route_direct_answer(question)
    if direct_answer and answer_scope != "book_only":
        answer_type = _select_answer_type(direct_answer.intent, preferred_answer_type)
        diagnostics.update(
            {
                "intent": direct_answer.intent,
                "rule_engine": "direct_router",
                "route": direct_answer.route,
                "grounding": direct_answer.grounding,
                "answer_scope": answer_scope,
                "retrieved_chunks": [],
                "selected_context": [],
                "rag_search_skipped": True,
                "fallback_used": "local_router",
            }
        )
        return _finalize_answer({
            "answer": direct_answer.answer,
            "answer_type": answer_type,
            "route": direct_answer.route,
            "grounding": direct_answer.grounding,
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
        }, question)

    logger.info("Ask intent classified: %s for query: %s", intent, question[:80])
    if dictionary_entry and (explicit_book or answer_scope == "book_only"):
        retrieval_question = f"{dictionary_entry.entity_ar} {' '.join(dictionary_entry.book_validation_terms)}"
    elif entity and intent == "definition_lookup":
        retrieval_question = entity.rewrite
    else:
        retrieval_question = question

    semantic_result = await semantic_retrieve_context(
        db,
        retrieval_question,
        user_id=user_id,
        lesson_id=lesson_id,
        topic_id=topic_id,
        source_types=routed_source_types,
        top_k=6,
        intent=intent,
    )
    chunks = semantic_result.chunks
    semantic_diagnostics = semantic_result.diagnostics
    diagnostics["semantic_rag"] = {
        "pipeline": semantic_diagnostics.get("pipeline"),
        "cache_hit": semantic_diagnostics.get("cache_hit"),
        "source_route": semantic_diagnostics.get("source_route"),
        "rewritten_query": semantic_diagnostics.get("rewritten_query"),
        "multi_queries": semantic_diagnostics.get("multi_queries"),
        "variant_count": semantic_diagnostics.get("variant_count"),
        "fused_candidate_count": semantic_diagnostics.get("fused_candidate_count"),
        "reranker_used": semantic_diagnostics.get("reranker_used"),
        "reranker_model": semantic_diagnostics.get("reranker_model"),
        "reranked_candidates": semantic_diagnostics.get("reranked_candidates"),
        "quality_gate": semantic_diagnostics.get("quality_gate"),
    }
    page_numbers = sorted({chunk.page_number for chunk in chunks if chunk.page_number is not None})
    diagnostics.update(
        {
            "retrieved_chunk_ids": [chunk.id for chunk in chunks],
            "retrieved_pages": page_numbers,
            "top_score": max((chunk.similarity_score for chunk in chunks), default=0.0),
            "selected_context": [
                {
                    "chunk_id": chunk.id,
                    "page": chunk.page_number,
                    "score": round(float(chunk.similarity_score), 4),
                    "preview": _chunk_preview(chunk),
                }
                for chunk in chunks
            ],
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

    if dictionary_entry and intent in simple_dictionary_intents and (explicit_book or answer_scope == "book_only"):
        if answer_scope == "book_only":
            if not dictionary_valid_chunks:
                return _finalize_answer(_not_found_response(
                    question=question,
                    answer_scope=answer_scope,
                    preferred_answer_type=preferred_answer_type,
                    diagnostics=diagnostics,
                    chunks=chunks,
                    rejected_chunks=dictionary_rejected_chunks,
                ), question)
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
            return _finalize_answer({
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
            }, question)

        if dictionary_valid_chunks:
            return _finalize_answer(_dictionary_response(
                entry=dictionary_entry,
                question=question,
                answer_scope=answer_scope,
                preferred_answer_type=preferred_answer_type,
                route="book_supported_dictionary",
                grounding="mixed",
                diagnostics=diagnostics,
                chunks=dictionary_valid_chunks,
                rejected_chunks=dictionary_rejected_chunks,
            ), question)
        return _finalize_answer(_dictionary_response(
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
        ), question)

    if intent == "definition_lookup" and entity:
        supporting_chunks, rejected_chunks = _definition_context(entity, chunks)
        if answer_scope == "book_only" and not supporting_chunks:
            return _finalize_answer(_not_found_response(
                question=question,
                answer_scope=answer_scope,
                preferred_answer_type=preferred_answer_type,
                diagnostics=diagnostics,
                chunks=chunks,
                rejected_chunks=rejected_chunks,
            ), question)
        return _finalize_answer(_direct_definition_response(
            entity=entity,
            chunks=chunks,
            preferred_answer_type=preferred_answer_type,
            diagnostics=diagnostics,
            answer_scope=answer_scope,
            route="textbook_rag" if supporting_chunks else "book_first",
            grounding="book" if supporting_chunks else "approved_dictionary",
        ), question)

    confidence_threshold = _confidence_threshold_for_intent(intent)
    if confidence < confidence_threshold:
        if answer_scope == "book_only":
            return _finalize_answer(_not_found_response(
                question=question,
                answer_scope=answer_scope,
                preferred_answer_type=preferred_answer_type,
                diagnostics=diagnostics,
                chunks=chunks,
            ), question)
        # Otherwise, for 'auto' and 'tutor_general' scopes, let the request proceed to
        # Gemini. The revised system prompts instruct it to use general knowledge when
        # book context is insufficient.

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
        diagnostics=diagnostics,
    )
    answer_type = _select_answer_type(intent, preferred_answer_type)
    diagnostics.update(
        {
            "low_confidence": False,
            "fallback_used": diagnostics.get("fallback_used"),
            "route": "textbook_rag",
            "grounding": "book",
        }
    )
    diagnostics["confidence_components"]["final_confidence"] = round(float(confidence), 4)
    return _finalize_answer({
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
    }, question)


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
