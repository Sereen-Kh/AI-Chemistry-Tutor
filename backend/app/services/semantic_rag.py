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
from app.services.gemini_client import get_gemini_client, is_gemini_auth_error, is_gemini_quota_error
from app.services.rag import (
    RetrievedChunk,
    clean_query,
    lexical_relevance_score,
    retrieve_context,
    rewrite_query,
)
from app.services.source_router import SourceRoute, route_source

logger = logging.getLogger(__name__)

_REWRITE_CACHE_TTL_SECONDS = 600
_RESULT_CACHE_TTL_SECONDS = 3600
_CACHE_VERSION = "v1"
_RRF_K = 60
_MAX_RERANK_CANDIDATES = 16


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


def _chunk_to_dict(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "source_id": chunk.source_id,
        "content": chunk.content,
        "source": chunk.source,
        "source_type": chunk.source_type,
        "content_type": chunk.content_type,
        "page_number": chunk.page_number,
        "chapter_id": chunk.chapter_id,
        "lesson_id": chunk.lesson_id,
        "topic_id": chunk.topic_id,
        "metadata_json": chunk.metadata_json,
        "similarity_score": chunk.similarity_score,
    }


def _chunk_from_dict(payload: dict[str, Any]) -> RetrievedChunk:
    return RetrievedChunk(**payload)


async def _gemini_json(prompt: str, *, max_output_tokens: int = 2048) -> Any | None:
    if not settings.effective_gemini_api_key:
        return None

    def _call() -> Any | None:
        from google.genai import types

        client = get_gemini_client()
        response = client.models.generate_content(
            model=settings.gemini_reranker_model,
            contents=prompt,
            config=types.GenerateContentConfig(
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
            logger.info("Gemini semantic RAG helper unavailable: %s", exc)
        else:
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
    chapter_id: int | None,
    lesson_id: int | None,
    topic_id: int | None,
    top_k: int,
    intent: str,
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
            chapter_id=chapter_id,
            lesson_id=lesson_id,
            topic_id=topic_id,
            source_types=source_types,
            top_k=top_k,
            min_similarity=0.0,
            intent=intent,
            diagnostics_callback=diagnostics.update,
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


def _fallback_rerank_score(query: str, candidate: FusedCandidate) -> float:
    lexical = lexical_relevance_score(query, candidate.chunk.content)
    return (0.55 * candidate.rrf_score) + (0.35 * candidate.retrieval_score) + (0.10 * lexical)


async def _gemini_rerank(query: str, candidates: list[FusedCandidate]) -> dict[int, dict[str, Any]] | None:
    if not settings.effective_gemini_api_key or not candidates:
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


async def _rerank(query: str, fused: list[FusedCandidate], top_k: int) -> tuple[list[RetrievedChunk], dict[str, Any]]:
    candidate_pool = fused[: max(top_k * 4, _MAX_RERANK_CANDIDATES)]
    gemini_scores = await _gemini_rerank(query, candidate_pool)
    diagnostics: dict[str, Any] = {
        "reranker_model": settings.gemini_reranker_model,
        "reranker_used": bool(gemini_scores),
    }

    scored: list[tuple[float, FusedCandidate, str]] = []
    for candidate in candidate_pool:
        if gemini_scores and candidate.chunk.id in gemini_scores:
            gemini_score = float(gemini_scores[candidate.chunk.id]["score"])
            score = (0.72 * gemini_score) + (0.18 * candidate.rrf_score) + (0.10 * candidate.retrieval_score)
            reason = str(gemini_scores[candidate.chunk.id].get("reason") or "gemini_rerank")
        else:
            score = _fallback_rerank_score(query, candidate)
            reason = "fallback_rrf_lexical"
        scored.append((score, candidate, reason))

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
    return final_chunks, diagnostics


async def semantic_retrieve_context(
    db: AsyncSession,
    query: str,
    *,
    user_id: int | None = None,
    source_types: list[str] | None = None,
    chapter_id: int | None = None,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    top_k: int = 5,
    intent: str = "general",
) -> SemanticRagResult:
    """Run the full semantic RAG retrieval pipeline."""
    start = time.monotonic()
    source_route: SourceRoute = await route_source(query, source_types)
    resolved_source_types = source_route.source_types
    cache_key = "semantic_rag:result:" + _CACHE_VERSION + ":" + _hash_payload(
        query, resolved_source_types, chapter_id, lesson_id, topic_id, top_k, intent
    )
    cached = await _redis_get_json(cache_key)
    if isinstance(cached, dict) and isinstance(cached.get("chunks"), list):
        chunks = [_chunk_from_dict(item) for item in cached["chunks"]]
        diagnostics = dict(cached.get("diagnostics") or {})
        diagnostics["cache_hit"] = True
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
                chapter_id=chapter_id,
                lesson_id=lesson_id,
                topic_id=topic_id,
                top_k=retrieval_top_k,
                intent=intent,
            )
            for label, variant_query in deduped_variants
        ]
    )
    fused = _rrf_fuse(list(variant_results))
    final_chunks, rerank_diagnostics = await _rerank(query, fused, top_k)

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
    return SemanticRagResult(chunks=final_chunks, diagnostics=diagnostics)
