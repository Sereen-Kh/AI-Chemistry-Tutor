"""Failure-tolerant persistent logging for RAG retrieval quality."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from app.core.config import settings
from app.database import AsyncSessionLocal
from app.models.rag_logging import RagQueryLog, RetrievedChunkLog
from app.services.embeddings import current_embedding_model_name

logger = logging.getLogger(__name__)


def _score(chunk: Any) -> float | None:
    value = getattr(chunk, "similarity_score", None)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


async def log_rag_retrieval(
    *,
    user_id: int | None,
    query_text: str,
    normalized_query: str | None,
    route: str,
    source_mode: str | None,
    top_k: int,
    min_similarity: float,
    chunks: Sequence[Any],
    retrieval_latency_ms: int | None = None,
    generation_latency_ms: int | None = None,
    answer_confidence: float | None = None,
    metadata_json: dict[str, Any] | None = None,
    used_chunk_ids: set[int] | None = None,
) -> int | None:
    """Persist a RAG query log.

    Observability must never break answer retrieval. This function uses its own
    short-lived session and catches all database errors.
    """
    if not settings.rag_query_logging_enabled:
        return None

    scores = [score for chunk in chunks if (score := _score(chunk)) is not None]
    max_similarity = max(scores) if scores else None
    avg_similarity = _average(scores)
    confidence = answer_confidence if answer_confidence is not None else max_similarity
    low_confidence = bool(confidence is None or confidence < min_similarity)
    used_chunk_ids = used_chunk_ids or set()
    total_latency_ms = None
    if retrieval_latency_ms is not None or generation_latency_ms is not None:
        total_latency_ms = int(retrieval_latency_ms or 0) + int(generation_latency_ms or 0)

    try:
        async with AsyncSessionLocal() as db:
            log = RagQueryLog(
                user_id=user_id,
                query_text=query_text,
                normalized_query=normalized_query,
                route=route,
                source_mode=source_mode,
                top_k=top_k,
                min_similarity=float(min_similarity),
                embedding_model=current_embedding_model_name(),
                retrieval_latency_ms=retrieval_latency_ms,
                generation_latency_ms=generation_latency_ms,
                total_latency_ms=total_latency_ms,
                result_count=len(chunks),
                max_similarity=max_similarity,
                avg_similarity=avg_similarity,
                low_confidence=low_confidence,
                answer_confidence=answer_confidence,
                metadata_json=metadata_json or {},
            )
            db.add(log)
            await db.flush()
            for rank, chunk in enumerate(chunks, start=1):
                score = _score(chunk)
                db.add(
                    RetrievedChunkLog(
                        rag_query_log_id=log.id,
                        chunk_id=getattr(chunk, "id", None),
                        source_id=getattr(chunk, "source_id", None),
                        source_type=getattr(chunk, "source_type", None),
                        page_number=getattr(chunk, "page_number", None),
                        content_type=getattr(chunk, "content_type", None),
                        rank=rank,
                        similarity_score=score,
                        hybrid_score=score,
                        rerank_score=None,
                        used_in_answer=bool(getattr(chunk, "id", None) in used_chunk_ids),
                    )
                )
            await db.commit()
            return log.id
    except Exception as exc:  # pragma: no cover - defensive observability path
        logger.warning("Failed to persist RAG query log: %s", exc, exc_info=True)
        return None
