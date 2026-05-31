"""Retrieval-Augmented Generation helpers."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.textbook import RagChunk
from app.services.embeddings import embed_query

_CACHE: dict[str, tuple[float, list["RetrievedChunk"]]] = {}
_CACHE_TTL_SECONDS = 3600


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


async def retrieve_context(
    db: Session,
    query: str,
    user_id: int | None = None,
    chapter_id: int | None = None,
    lesson_id: int | None = None,
    topic_id: int | None = None,
    source_types: list[str] | None = None,
    content_types: list[str] | None = None,
    top_k: int = 6,
    min_similarity: float = 0.0,
) -> list[RetrievedChunk]:
    """Retrieve relevant source chunks for a query.

    Current local implementation ranks rows in Python so SQLite dev works. When
    running PostgreSQL + pgvector, this service can be swapped to the ivfflat SQL
    query without changing callers.
    """
    cache_key = (
        f"{query}|{user_id}|{chapter_id}|{lesson_id}|{topic_id}|"
        f"{source_types}|{content_types}|{top_k}|{min_similarity}"
    )
    cached = _CACHE.get(cache_key)
    if cached and cached[0] > time.time():
        return cached[1]

    query_embedding = await embed_query(query)
    sql = db.query(RagChunk).filter(RagChunk.embedding.isnot(None))
    if chapter_id is not None:
        sql = sql.filter(RagChunk.chapter_id == chapter_id)
    if lesson_id is not None:
        sql = sql.filter(RagChunk.lesson_id == lesson_id)
    if topic_id is not None:
        sql = sql.filter(RagChunk.topic_id == topic_id)
    if source_types:
        sql = sql.filter(RagChunk.source_type.in_(source_types))
    if content_types:
        sql = sql.filter(RagChunk.content_type.in_(content_types))

    scored: list[RetrievedChunk] = []
    for chunk in sql.all():
        score = _cosine_similarity(query_embedding, chunk.embedding or [])
        if score >= min_similarity:
            scored.append(
                RetrievedChunk(
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
            )

    scored.sort(key=lambda item: item.similarity_score, reverse=True)
    result = scored[:top_k]
    _CACHE[cache_key] = (time.time() + _CACHE_TTL_SECONDS, result)
    return result


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks for insertion into an AI system prompt."""
    parts = []
    for chunk in chunks:
        ref = f"صفحة {chunk.page_number}" if chunk.page_number else chunk.source or "الكتاب"
        parts.append(f"{chunk.content}\n[المصدر: {ref}, النوع: {chunk.source_type}/{chunk.content_type}]")
    return "\n\n---\n\n".join(parts)
