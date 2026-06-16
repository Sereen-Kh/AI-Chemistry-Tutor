"""Semantic RAG pipeline over PostgreSQL/pgvector.

This module keeps the production vector store as PostgreSQL/pgvector and adds
semantic orchestration on top of the existing `retrieve_context` primitive.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import logging
import re
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis_client
from app.database import AsyncSessionLocal
from app.services.gemini_client import (
    get_gemini_client,
    is_gemini_auth_error,
    is_gemini_quota_error,
    semantic_helper_http_options,
)
from app.services.rag import (
    RetrievedChunk,
    clean_query,
    lexical_relevance_score,
    retrieve_context,
    rewrite_query,
)
from app.services.rag_logging import log_rag_retrieval
from app.services.source_router import SourceRoute, route_source

logger = logging.getLogger(__name__)

_REWRITE_CACHE_TTL_SECONDS = 600
_RESULT_CACHE_TTL_SECONDS = 3600
_CACHE_VERSION = "v3"
_GEMINI_HELPER_DISABLED_UNTIL = 0.0
_GEMINI_HELPER_DISABLED_REASON = ""
_RRF_K = 60
_MAX_RERANK_CANDIDATES = 16
_QUALITY_GATE_MIN_SCORE = 0.45
_INTENT_MIN_SCORES = {
    "definition_lookup": 0.52,
    "property_lookup": 0.50,
    "formula_lookup": 0.48,
    "equation_lookup": 0.48,
    "reaction_query": 0.48,
    "table_lookup": 0.48,
    "book_grounded": 0.45,
    "exercise_lookup": 0.42,
    "exercise_solving": 0.42,
    "safety_question": 0.45,
    "general": 0.45,
}
_INTENT_PREFERRED_CONTENT_TYPES = {
    "definition_lookup": {"definition", "text", "result", "learned_summary", "summary", "concept"},
    "property_lookup": {"definition", "text", "result", "learned_summary", "table"},
    "formula_lookup": {"formula", "equation", "table", "definition", "text"},
    "equation_lookup": {"equation", "result", "exercise", "text", "table"},
    "reaction_query": {"equation", "result", "exercise", "text", "table"},
    "table_lookup": {"table", "text"},
    "exercise_lookup": {"exercise", "equation", "result", "table", "text"},
    "exercise_solving": {"exercise", "equation", "result", "table", "text"},
    "safety_question": {"warning", "safety", "objective", "objectives", "text", "learned_summary"},
    "book_grounded": {"definition", "text", "result", "learned_summary", "table"},
}
_INTENT_PENALIZED_CONTENT_TYPES = {
    "definition_lookup": {"exercise", "question", "questions", "exam_question", "objectives", "objective"},
    "property_lookup": {"exercise", "question", "questions", "exam_question", "objectives", "objective"},
    "formula_lookup": {"objectives", "objective"},
    "table_lookup": {"exercise", "question", "questions"},
    "safety_question": {"definition", "exercise", "question", "questions", "exam_question"},
}
_ENTITY_COVERAGE_GROUPS = (
    ("sodium_carbonate", ("كربونات الصوديوم", "na2co3")),
    ("calcium_carbonate", ("كربونات الكالسيوم", "caco3")),
    ("sodium_bicarbonate", ("بيكربونات الصوديوم", "nahco3")),
    ("potassium_hydroxide", ("هيدروكسيد البوتاسيوم", "koh")),
    ("copper", ("نحاس", "النحاس", "cu")),
    ("iron", ("حديد", "الحديد", "fe")),
    ("zinc", ("زنك", "الزنك", "خارصين", "zn")),
    ("sulfuric_acid", ("حمض الكبريت", "h2so4")),
    ("hydrochloric_acid", ("حمض كلور الماء", "كلور الهيدروجين", "hcl")),
    ("ammonia", ("النشادر", "nh3")),
    ("ammonium_chloride", ("كلوريد الامونيوم", "كلوريد الأمونيوم", "nh4cl")),
    ("water_decomposition", ("تفكك الماء", "وعاء فولتا")),
)
_ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
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


@dataclass(frozen=True)
class FusedCandidate:
    chunk: RetrievedChunk
    rrf_score: float
    retrieval_score: float
    origins: list[str]


@dataclass(frozen=True)
class SemanticRagResult:
    chunks: list[RetrievedChunk]
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class SemanticSearchResult:
    chunk_id: int
    source_type: str
    score: float
    content: str
    page_start: int | None
    page_end: int | None
    chapter_title: str | None
    lesson_title: str | None
    chunk_type: str
    exercise_number: str | None
    question_number: str | None
    metadata: dict[str, Any]


def _safe_json_loads(raw: str) -> Any:
    cleaned = (raw or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)


async def _redis_get_json(key: str) -> Any | None:
    redis = get_redis_client()
    try:
        cached = await redis.get(key)
        return json.loads(cached) if cached else None
    except Exception:
        return None
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass


async def _redis_set_json(key: str, payload: Any, ttl_seconds: int) -> None:
    redis = get_redis_client()
    try:
        await redis.setex(key, ttl_seconds, json.dumps(payload, ensure_ascii=False))
    except Exception:
        pass
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass


def _hash_payload(*parts: object) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def _normalize_relevance_text(text: str) -> str:
    lowered = (text or "").lower().replace("ـ", "")
    lowered = _ARABIC_DIACRITICS_RE.sub("", lowered)
    lowered = lowered.translate(_ARABIC_NORMALIZATION)
    lowered = re.sub(r"[؟?!.،,؛;:()\[\]{}$\\_]+", " ", lowered)
    return " ".join(lowered.split()).strip()


def _chunk_to_dict(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "source_id": chunk.source_id,
        "content": chunk.content,
        "source": chunk.source,
        "source_type": chunk.source_type,
        "content_type": chunk.content_type,
        "page_number": chunk.page_number,
        "unit_id": chunk.unit_id,
        "chapter_id": chunk.chapter_id,
        "lesson_id": chunk.lesson_id,
        "topic_id": chunk.topic_id,
        "metadata_json": chunk.metadata_json,
        "similarity_score": chunk.similarity_score,
    }


def _chunk_from_dict(payload: dict[str, Any]) -> RetrievedChunk:
    payload.setdefault("unit_id", None)
    return RetrievedChunk(**payload)


async def _gemini_json(prompt: str, *, max_output_tokens: int = 2048) -> Any | None:
    global _GEMINI_HELPER_DISABLED_REASON, _GEMINI_HELPER_DISABLED_UNTIL
    if not settings.gemini_semantic_helpers_enabled or not settings.effective_gemini_api_key:
        return None
    if _GEMINI_HELPER_DISABLED_UNTIL > time.monotonic():
        return None

    def _call() -> Any | None:
        from google.genai import types

        client = get_gemini_client()
        response = client.models.generate_content(
            model=settings.gemini_reranker_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                http_options=semantic_helper_http_options(),
                response_mime_type="application/json",
                temperature=0.0,
                max_output_tokens=max_output_tokens,
            ),
        )
        text = response.text or ""
        return _safe_json_loads(text)

    try:
        return await asyncio.to_thread(_call)
    except Exception as exc:  # pragma: no cover - external model behavior
        if is_gemini_auth_error(exc) or is_gemini_quota_error(exc):
            _GEMINI_HELPER_DISABLED_REASON = "auth_or_quota_error"
            _GEMINI_HELPER_DISABLED_UNTIL = time.monotonic() + max(1, settings.gemini_failure_cooldown_seconds)
            logger.info("Gemini semantic RAG helper unavailable: %s", exc)
        else:
            _GEMINI_HELPER_DISABLED_REASON = "service_error"
            _GEMINI_HELPER_DISABLED_UNTIL = time.monotonic() + 60
            logger.warning("Gemini semantic RAG helper failed: %s", exc)
        return None


async def rewrite_student_query(query: str) -> str:
    """Stage 1: rewrite/expand a student query for chemistry retrieval."""
    cache_key = "semantic_rag:rewrite:" + _CACHE_VERSION + ":" + _hash_payload(query)
    cached = await _redis_get_json(cache_key)
    if isinstance(cached, dict) and cached.get("rewritten_query"):
        return str(cached["rewritten_query"])

    prompt = (
        "أعد صياغة سؤال طالب الصف التاسع التالي كسؤال بحث عربي قصير للكيمياء. "
        "أضف فقط المصطلحات الكيميائية المهمة، ولا تجب عن السؤال. "
        'أعد JSON فقط بالشكل {"rewritten_query": "..."}.\n\n'
        f"السؤال: {query}"
    )
    payload = await _gemini_json(prompt, max_output_tokens=512)
    rewritten = ""
    if isinstance(payload, dict):
        rewritten = str(payload.get("rewritten_query") or "").strip()
    if not rewritten:
        rewritten = rewrite_query(clean_query(query)) or clean_query(query)
    await _redis_set_json(cache_key, {"rewritten_query": rewritten}, _REWRITE_CACHE_TTL_SECONDS)
    return rewritten


async def generate_hyde_answer(query: str) -> str:
    """Stage 2: generate a hypothetical source-grounded answer for HyDE retrieval."""
    cache_key = "semantic_rag:hyde:" + _CACHE_VERSION + ":" + _hash_payload(query)
    cached = await _redis_get_json(cache_key)
    if isinstance(cached, dict) and cached.get("hyde"):
        return str(cached["hyde"])

    prompt = (
        "اكتب فقرة عربية قصيرة تشبه جواب كتاب كيمياء للصف التاسع عن السؤال التالي. "
        "الغرض هو البحث الدلالي فقط؛ لا تضف معلومات غير مرتبطة. "
        'أعد JSON فقط بالشكل {"hyde": "..."}.\n\n'
        f"السؤال: {query}"
    )
    payload = await _gemini_json(prompt, max_output_tokens=900)
    hyde = ""
    if isinstance(payload, dict):
        hyde = str(payload.get("hyde") or "").strip()
    if not hyde:
        hyde = rewrite_query(clean_query(query)) or clean_query(query)
    await _redis_set_json(cache_key, {"hyde": hyde}, _REWRITE_CACHE_TTL_SECONDS)
    return hyde


async def generate_multi_queries(query: str) -> list[str]:
    """Stage 3: generate alternative Arabic query formulations."""
    cache_key = "semantic_rag:multi:" + _CACHE_VERSION + ":" + _hash_payload(query)
    cached = await _redis_get_json(cache_key)
    if isinstance(cached, dict) and isinstance(cached.get("queries"), list):
        return [str(item) for item in cached["queries"] if str(item).strip()][:3]

    prompt = (
        "اكتب ثلاث صيغ بحث عربية قصيرة ومختلفة لسؤال طالب كيمياء صف تاسع. "
        'أعد JSON فقط بالشكل {"queries": ["...", "...", "..."]}.\n\n'
        f"السؤال: {query}"
    )
    payload = await _gemini_json(prompt, max_output_tokens=700)
    queries: list[str] = []
    if isinstance(payload, dict) and isinstance(payload.get("queries"), list):
        queries = [str(item).strip() for item in payload["queries"] if str(item).strip()]
    if not queries:
        cleaned = clean_query(query)
        rewritten = rewrite_query(cleaned)
        queries = [item for item in [cleaned, rewritten] if item]
    queries = list(dict.fromkeys(queries))[:3]
    await _redis_set_json(cache_key, {"queries": queries}, _REWRITE_CACHE_TTL_SECONDS)
    return queries


async def _retrieve_variant(
    db: AsyncSession,
    *,
    label: str,
    query: str,
    user_id: int | None,
    source_types: list[str],
    unit_id: int | None,
    chapter_id: int | None,
    lesson_id: int | None,
    topic_id: int | None,
    top_k: int,
    intent: str,
    document_type: str | None = None,
) -> tuple[str, list[RetrievedChunk], dict[str, Any]]:
    diagnostics: dict[str, Any] = {}
    # SQLAlchemy AsyncSession does not permit concurrent operations. Semantic
    # retrieval intentionally runs query variants in parallel, so each variant
    # gets its own short-lived session while the caller's session stays untouched.
    async with AsyncSessionLocal() as variant_db:
        chunks = await retrieve_context(
            variant_db,
            query,
            user_id=user_id,
            unit_id=unit_id,
            chapter_id=chapter_id,
            lesson_id=lesson_id,
            topic_id=topic_id,
            source_types=source_types,
            top_k=top_k,
            min_similarity=0.0,
            intent=intent,
            diagnostics_callback=diagnostics.update,
            document_type=document_type,
            log_retrieval=False,
        )
    return label, chunks, diagnostics


def _rrf_fuse(variant_results: list[tuple[str, list[RetrievedChunk], dict[str, Any]]]) -> list[FusedCandidate]:
    by_id: dict[int, dict[str, Any]] = {}
    for label, chunks, _diagnostics in variant_results:
        for rank, chunk in enumerate(chunks, start=1):
            state = by_id.setdefault(
                chunk.id,
                {
                    "chunk": chunk,
                    "rrf_score": 0.0,
                    "retrieval_score": 0.0,
                    "origins": [],
                },
            )
            state["rrf_score"] += 1.0 / (_RRF_K + rank)
            state["retrieval_score"] = max(float(state["retrieval_score"]), float(chunk.similarity_score or 0.0))
            state["origins"].append(label)

    fused = [
        FusedCandidate(
            chunk=state["chunk"],
            rrf_score=float(state["rrf_score"]),
            retrieval_score=float(state["retrieval_score"]),
            origins=list(dict.fromkeys(state["origins"])),
        )
        for state in by_id.values()
    ]
    fused.sort(key=lambda item: (item.rrf_score, item.retrieval_score), reverse=True)
    return fused


def _content_type_adjustment(query: str, candidate: FusedCandidate, *, intent: str) -> tuple[float, list[str]]:
    content_type = (candidate.chunk.content_type or "text").strip().lower()
    query_norm = _normalize_relevance_text(query)
    content_norm = _normalize_relevance_text(candidate.chunk.content)
    adjustment = 0.0
    reasons: list[str] = []

    preferred = _INTENT_PREFERRED_CONTENT_TYPES.get(intent, set())
    penalized = _INTENT_PENALIZED_CONTENT_TYPES.get(intent, set())
    if content_type in preferred:
        adjustment += 0.08
        reasons.append(f"preferred_content_type:{content_type}")
    if content_type in penalized:
        adjustment -= 0.18
        reasons.append(f"penalized_content_type:{content_type}")

    if intent == "definition_lookup":
        if any(marker in content_norm for marker in ("الاهداف", "يتعرف", "يميز", "اختر الاجابه")):
            adjustment -= 0.12
            reasons.append("definition_noise_marker")
        if any(marker in content_norm for marker in ("مواد تعطي", "هو عدد", "هي مواد", "يتشكل الملح")):
            adjustment += 0.12
            reasons.append("definition_evidence_marker")

    acid_to_water_query = (
        "حمض" in query_norm
        and "ماء" in query_norm
        and any(term in query_norm for term in ("نضيف", "اضف", "اضافه", "اضافة", "العكس", "وليس"))
    )
    acid_to_water_warning = (
        "حمض" in content_norm
        and "ماء" in content_norm
        and any(term in content_norm for term in ("اضف الحمض الى الماء", "اضافه الحمض الى الماء", "تحذير"))
    )
    if acid_to_water_query:
        if acid_to_water_warning:
            adjustment += 0.36
            reasons.append("acid_to_water_safety_warning")
        elif (
            "ايونات الهدروجين" in content_norm
            or "ايونات الهيدروجين" in content_norm
            or "h+" in content_norm
            or "مواد تعطي عند انحلالها" in content_norm
        ):
            adjustment -= 0.55
            reasons.append("acid_definition_not_safety_answer")

    for entity_key, aliases in _ENTITY_COVERAGE_GROUPS:
        query_mentions_entity = any(alias in query_norm for alias in aliases)
        if not query_mentions_entity:
            continue
        content_mentions_entity = any(alias in content_norm for alias in aliases)
        if content_mentions_entity:
            adjustment += 0.12
            reasons.append(f"exact_entity:{entity_key}")
        else:
            adjustment -= 0.20
            reasons.append(f"missing_entity:{entity_key}")

    if any(term in query_norm for term in ("املاح", "الاملاح", "ملح", "الملح")):
        if any(term in content_norm for term in ("ايونات الملح", "اسم الملح", "يتشكل الملح", "الصيغه الجزيئيه")):
            adjustment += 0.14
            reasons.append("salt_evidence")

    return adjustment, reasons


def _semantic_relevance_score(
    query: str,
    candidate: FusedCandidate,
    *,
    intent: str,
    gemini_score: float | None = None,
) -> tuple[float, list[str]]:
    lexical = lexical_relevance_score(query, candidate.chunk.content)
    rrf_signal = min(candidate.rrf_score * 4.0, 0.18)
    adjustment, reasons = _content_type_adjustment(query, candidate, intent=intent)

    if gemini_score is None:
        score = (0.68 * candidate.retrieval_score) + (0.24 * lexical) + rrf_signal + adjustment
        reasons.append("fallback_retrieval_lexical_rrf")
    else:
        score = (0.46 * gemini_score) + (0.34 * candidate.retrieval_score) + (0.14 * lexical) + rrf_signal + adjustment
        reasons.append("gemini_retrieval_lexical_rrf")

    return round(max(0.0, min(1.0, score)), 4), reasons


async def _gemini_rerank(query: str, candidates: list[FusedCandidate]) -> dict[int, dict[str, Any]] | None:
    if not settings.gemini_semantic_helpers_enabled or not settings.effective_gemini_api_key or not candidates:
        return None

    payload = [
        {
            "chunk_id": candidate.chunk.id,
            "source_type": candidate.chunk.source_type,
            "page": candidate.chunk.page_number,
            "content_type": candidate.chunk.content_type,
            "snippet": candidate.chunk.content[:900],
        }
        for candidate in candidates[:_MAX_RERANK_CANDIDATES]
    ]
    prompt = (
        "قيّم صلة كل مقطع بسؤال طالب كيمياء عربي. أعط درجة من 0 إلى 10. "
        "فضّل المقاطع التي تجيب مباشرة وتحتوي صيغاً/مصطلحات مطابقة. "
        'أعد JSON فقط بالشكل {"scores": [{"chunk_id": 1, "score": 8.5, "reason": "..."}]}.\n\n'
        f"السؤال: {query}\n\n"
        f"المقاطع: {json.dumps(payload, ensure_ascii=False)}"
    )
    result = await _gemini_json(prompt, max_output_tokens=2200)
    if not isinstance(result, dict) or not isinstance(result.get("scores"), list):
        return None
    scores: dict[int, dict[str, Any]] = {}
    for item in result["scores"]:
        if not isinstance(item, dict):
            continue
        try:
            chunk_id = int(item["chunk_id"])
            score = max(0.0, min(10.0, float(item.get("score", 0.0))))
        except (KeyError, TypeError, ValueError):
            continue
        scores[chunk_id] = {"score": score / 10.0, "reason": str(item.get("reason") or "")}
    return scores or None


def _minimum_score_for_intent(intent: str) -> float:
    return max(_QUALITY_GATE_MIN_SCORE, _INTENT_MIN_SCORES.get(intent, _INTENT_MIN_SCORES["general"]))


async def _rerank(
    query: str,
    fused: list[FusedCandidate],
    top_k: int,
    *,
    intent: str,
) -> tuple[list[RetrievedChunk], dict[str, Any]]:
    candidate_pool = fused[: max(top_k * 4, _MAX_RERANK_CANDIDATES)]
    gemini_scores = await _gemini_rerank(query, candidate_pool)
    min_score = _minimum_score_for_intent(intent)
    diagnostics: dict[str, Any] = {
        "reranker_model": settings.gemini_reranker_model,
        "semantic_helpers_enabled": settings.gemini_semantic_helpers_enabled,
        "semantic_helper_disabled_reason": _GEMINI_HELPER_DISABLED_REASON or None,
        "reranker_used": bool(gemini_scores),
        "quality_gate_min_score": min_score,
    }

    scored: list[tuple[float, FusedCandidate, str]] = []
    rejected: list[dict[str, Any]] = []
    for candidate in candidate_pool:
        if gemini_scores and candidate.chunk.id in gemini_scores:
            gemini_score = float(gemini_scores[candidate.chunk.id]["score"])
            score, reasons = _semantic_relevance_score(query, candidate, intent=intent, gemini_score=gemini_score)
            reason = str(gemini_scores[candidate.chunk.id].get("reason") or "gemini_rerank")
            if reasons:
                reason = f"{reason}; {';'.join(reasons)}"
        else:
            score, reasons = _semantic_relevance_score(query, candidate, intent=intent)
            reason = ";".join(reasons) or "fallback_retrieval_lexical_rrf"
        if score >= min_score:
            scored.append((score, candidate, reason))
        else:
            rejected.append(
                {
                    "chunk_id": candidate.chunk.id,
                    "page_number": candidate.chunk.page_number,
                    "source_type": candidate.chunk.source_type,
                    "content_type": candidate.chunk.content_type,
                    "score": round(float(score), 4),
                    "retrieval_score": round(candidate.retrieval_score, 4),
                    "reason": "below_quality_gate",
                }
            )

    scored.sort(key=lambda item: item[0], reverse=True)
    final_chunks = [
        replace(candidate.chunk, similarity_score=round(float(score), 4))
        for score, candidate, _reason in scored[:top_k]
    ]
    diagnostics["reranked_candidates"] = [
        {
            "chunk_id": candidate.chunk.id,
            "page_number": candidate.chunk.page_number,
            "source_type": candidate.chunk.source_type,
            "content_type": candidate.chunk.content_type,
            "score": round(float(score), 4),
            "rrf_score": round(candidate.rrf_score, 5),
            "retrieval_score": round(candidate.retrieval_score, 4),
            "origins": candidate.origins,
            "reason": reason,
        }
        for score, candidate, reason in scored[:top_k]
    ]
    diagnostics["quality_gate"] = {
        "min_score": min_score,
        "accepted_count": len(scored),
        "rejected_count": len(rejected),
        "rejected_candidates": rejected[:12],
    }
    return final_chunks, diagnostics


async def semantic_retrieve_context(
    db: AsyncSession,
    query: str,
    *,
    user_id: int | None = None,
    source_types: list[str] | None = None,
    unit_id: int | None = None,
    chapter_id: int | None = None,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    top_k: int = 5,
    intent: str = "general",
    document_type: str | None = None,
) -> SemanticRagResult:
    """Run the full semantic RAG retrieval pipeline."""
    start = time.monotonic()
    source_route: SourceRoute = await route_source(query, source_types)
    resolved_source_types = source_route.source_types
    cache_key = "semantic_rag:result:" + _CACHE_VERSION + ":" + _hash_payload(
        query, resolved_source_types, unit_id, chapter_id, lesson_id, topic_id, top_k, intent
    )
    cached = await _redis_get_json(cache_key)
    if isinstance(cached, dict) and isinstance(cached.get("chunks"), list):
        chunks = [_chunk_from_dict(item) for item in cached["chunks"]]
        diagnostics = dict(cached.get("diagnostics") or {})
        diagnostics["cache_hit"] = True
        await log_rag_retrieval(
            user_id=user_id,
            query_text=query,
            normalized_query=clean_query(query),
            route="semantic_retrieve",
            source_mode=",".join(resolved_source_types or []),
            top_k=top_k,
            min_similarity=_minimum_score_for_intent(intent),
            chunks=chunks,
            retrieval_latency_ms=diagnostics.get("retrieval_time_ms"),
            metadata_json={"cache_hit": True, "intent": intent, "diagnostics": diagnostics},
        )
        return SemanticRagResult(chunks=chunks, diagnostics=diagnostics)

    rewritten_query, hyde, multi_queries = await asyncio.gather(
        rewrite_student_query(query),
        generate_hyde_answer(query),
        generate_multi_queries(query),
    )

    query_variants: list[tuple[str, str]] = [
        ("original", query),
        ("rewritten", rewritten_query),
        ("hyde", hyde),
        *[(f"multi_{index}", item) for index, item in enumerate(multi_queries, start=1)],
    ]
    deduped_variants: list[tuple[str, str]] = []
    seen_queries: set[str] = set()
    for label, item in query_variants:
        cleaned = clean_query(item)
        if not cleaned or cleaned in seen_queries:
            continue
        seen_queries.add(cleaned)
        deduped_variants.append((label, item))

    retrieval_top_k = max(top_k * 4, 12)
    variant_results = await asyncio.gather(
        *[
            _retrieve_variant(
                db,
                label=label,
                query=variant_query,
                user_id=user_id,
                source_types=resolved_source_types,
                unit_id=unit_id,
                chapter_id=chapter_id,
                lesson_id=lesson_id,
                topic_id=topic_id,
                top_k=retrieval_top_k,
                intent=intent,
                document_type=document_type,
            )
            for label, variant_query in deduped_variants
        ]
    )
    fused = _rrf_fuse(list(variant_results))
    final_chunks, rerank_diagnostics = await _rerank(query, fused, top_k, intent=intent)

    diagnostics: dict[str, Any] = {
        "pipeline": "semantic_rag_pgvector",
        "cache_hit": False,
        "source_route": asdict(source_route),
        "source_types": resolved_source_types,
        "original_query": query,
        "rewritten_query": rewritten_query,
        "hyde": hyde,
        "multi_queries": multi_queries,
        "variant_labels": [label for label, _variant_query in deduped_variants],
        "variant_count": len(deduped_variants),
        "fused_candidate_count": len(fused),
        "retrieval_time_ms": int((time.monotonic() - start) * 1000),
        "variant_diagnostics": {label: diag for label, _chunks, diag in variant_results},
        **rerank_diagnostics,
    }
    await _redis_set_json(
        cache_key,
        {"chunks": [_chunk_to_dict(chunk) for chunk in final_chunks], "diagnostics": diagnostics},
        _RESULT_CACHE_TTL_SECONDS,
    )
    await log_rag_retrieval(
        user_id=user_id,
        query_text=query,
        normalized_query=clean_query(query),
        route="semantic_retrieve",
        source_mode=",".join(resolved_source_types or []),
        top_k=top_k,
        min_similarity=_minimum_score_for_intent(intent),
        chunks=final_chunks,
        retrieval_latency_ms=diagnostics.get("retrieval_time_ms"),
        metadata_json={"cache_hit": False, "intent": intent, "diagnostics": diagnostics},
    )
    return SemanticRagResult(chunks=final_chunks, diagnostics=diagnostics)


def _source_types_for_mode(mode: str, requested: list[str] | None) -> list[str] | None:
    if requested:
        return requested
    normalized = (mode or "balanced").strip().lower()
    if normalized == "solution_only":
        return ["solution_book"]
    if normalized == "textbook_only":
        return ["textbook"]
    return ["textbook", "solution_book"]


def _intent_for_search(query: str, mode: str, intent: str | None) -> str:
    if intent and intent != "general":
        return intent
    normalized = _normalize_relevance_text(query)
    if mode in {"solution_first", "solution_only"}:
        return "exercise_solving"
    if any(term in normalized for term in ("حل", "احسب", "مساله", "تمرين", "جواب", "سؤال")):
        return "exercise_solving"
    if any(term in normalized for term in ("تعريف", "ما هو", "ما هي", "اشرح")):
        return "definition_lookup"
    return "general"


def _metadata_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


async def semantic_search(
    db: AsyncSession,
    *,
    query: str,
    source_types: list[str] | None = None,
    top_k: int = 8,
    filters: dict[str, Any] | None = None,
    mode: str = "balanced",
    user_id: int | None = None,
    intent: str = "general",
    min_similarity: float = 0.45,
) -> tuple[list[SemanticSearchResult], dict[str, Any]]:
    """Search textbook and/or solution-book chunks with consistent metadata.

    This is a thin API-oriented wrapper over the existing embedding + hybrid
    retrieval stack. It adds source-mode routing and normalizes solution-book
    metadata into a stable result object for mobile and Swagger callers.
    """
    filters = filters or {}
    resolved_source_types = _source_types_for_mode(mode, source_types)
    resolved_intent = _intent_for_search(query, mode, intent)
    content_types = filters.get("content_types") or filters.get("chunk_types")
    if isinstance(content_types, str):
        content_types = [content_types]
    chunks = await retrieve_context(
        db,
        query=query,
        user_id=user_id,
        unit_id=filters.get("unit_id"),
        chapter_id=filters.get("chapter_id"),
        lesson_id=filters.get("lesson_id"),
        topic_id=filters.get("topic_id"),
        source_types=resolved_source_types,
        content_types=content_types,
        top_k=top_k,
        min_similarity=min_similarity,
        intent=resolved_intent,
        page_start=filters.get("page_start"),
        page_end=filters.get("page_end"),
        log_retrieval=False,
    )
    if mode == "solution_first":
        chunks.sort(key=lambda item: (item.source_type != "solution_book", -item.similarity_score))
    elif mode == "textbook_first":
        chunks.sort(key=lambda item: (item.source_type != "textbook", -item.similarity_score))

    results: list[SemanticSearchResult] = []
    for chunk in chunks[:top_k]:
        meta = _metadata_dict(chunk.metadata_json)
        page_start = meta.get("page_start") if meta.get("page_start") is not None else chunk.page_number
        page_end = meta.get("page_end") if meta.get("page_end") is not None else chunk.page_number
        results.append(
            SemanticSearchResult(
                chunk_id=chunk.id,
                source_type=chunk.source_type,
                score=chunk.similarity_score,
                content=chunk.content,
                page_start=page_start,
                page_end=page_end,
                chapter_title=meta.get("chapter_title"),
                lesson_title=meta.get("lesson_title"),
                chunk_type=chunk.content_type,
                exercise_number=meta.get("exercise_number"),
                question_number=meta.get("question_number"),
                metadata=meta,
            )
        )

    diagnostics = {
        "pipeline": "semantic_search_pgvector",
        "mode": mode,
        "intent": resolved_intent,
        "source_types": resolved_source_types,
        "filters": filters,
        "result_count": len(results),
    }
    await log_rag_retrieval(
        user_id=user_id,
        query_text=query,
        normalized_query=clean_query(query),
        route="semantic_search",
        source_mode=mode,
        top_k=top_k,
        min_similarity=min_similarity,
        chunks=chunks[:top_k],
        retrieval_latency_ms=None,
        metadata_json=diagnostics,
    )
    return results, diagnostics
