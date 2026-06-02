"""Retrieval-Augmented Generation helpers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis_client
from app.models.textbook import ContentSource, RagChunk
from app.services.embeddings import embed_query

_CACHE: dict[str, tuple[float, list["RetrievedChunk"]]] = {}
_CACHE_TTL_SECONDS = 3600
_CACHE_VERSION = "v3"
_RETRIEVABLE_SOURCE_STATUSES = ["completed", "completed_with_warnings", "dry_run_completed", "dry_run_incomplete"]

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
_QUERY_STOPWORDS = {
    "اشرح",
    "شرح",
    "فسر",
    "عرف",
    "تعريف",
    "ما",
    "ماذا",
    "من",
    "في",
    "عن",
    "على",
    "الى",
    "الي",
    "هو",
    "هي",
    "هذا",
    "هذه",
    "ذلك",
    "تلك",
    "لي",
    "لنا",
    "انا",
    "اريد",
    "بدي",
    "كتاب",
    "الكتاب",
    "كيمياء",
    "الكيمياء",
}
_TERM_EXPANSIONS = {
    "حموض": {
        "حموض",
        "الحموض",
        "حمض",
        "الحمض",
        "حمضي",
        "حمضيه",
        "الحمضيه",
        "احماض",
        "الاحماض",
        "هيدروجين",
        "الهيدروجين",
        "هدروجين",
        "الهدروجين",
        "هدرونيوم",
    },
    "حمض": {
        "حموض",
        "الحموض",
        "حمض",
        "الحمض",
        "حمضي",
        "حمضيه",
        "الحمضيه",
        "احماض",
        "الاحماض",
        "هيدروجين",
        "الهيدروجين",
        "هدروجين",
        "الهدروجين",
        "هدرونيوم",
    },
}


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


def _normalize_lexical_text(text: str) -> str:
    """Normalize Arabic text enough for lexical matching over noisy OCR chunks."""
    lowered = text.lower().replace("ـ", "")
    without_diacritics = _ARABIC_DIACRITICS_RE.sub("", lowered)
    return without_diacritics.translate(_ARABIC_NORMALIZATION)


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

    return round(min(score, 1.0), 4)


def _hybrid_score(query: str, content: str, vector_score: float) -> float:
    lexical_score = lexical_relevance_score(query, content)
    if lexical_score <= 0:
        return round(max(vector_score, 0.0), 4)
    blended = (0.35 * max(vector_score, 0.0)) + (0.65 * lexical_score)
    # Exact lexical matches in the textbook should outrank weak local/hash embeddings.
    return round(min(max(blended, lexical_score, vector_score), 1.0), 4)


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
) -> list[RetrievedChunk]:
    """Retrieve relevant source chunks for a query.

    Uses PostgreSQL pgvector if available, otherwise falls back to Python-based
    cosine similarity for SQLite local development. Uses Redis for caching.
    """
    cache_key_raw = (
        f"{query}|{user_id}|{chapter_id}|{lesson_id}|{topic_id}|"
        f"{source_types}|{content_types}|{top_k}|{min_similarity}"
    )
    cache_key = f"rag_cache:{_CACHE_VERSION}:" + hashlib.md5(cache_key_raw.encode()).hexdigest()

    redis = get_redis_client()
    try:
        cached = await redis.get(cache_key)
        if cached:
            chunks_dict = json.loads(cached)
            return [RetrievedChunk(**c) for c in chunks_dict]
    except Exception:
        pass
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass

    query_embedding = await embed_query(query)

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

    scored: list[RetrievedChunk] = []

    # Check if we are running on PostgreSQL
    is_postgres = db.bind.dialect.name == "postgresql" if db.bind else False

    if is_postgres:
        # pgvector SQL path (cosine distance)
        # Pull extra candidates, then rerank with lexical matches to handle Arabic OCR text.
        candidate_limit = max(top_k * 8, 32)
        stmt = stmt.order_by(RagChunk.embedding.cosine_distance(query_embedding)).limit(candidate_limit)
        result = await db.execute(stmt)
        for chunk in result.scalars().all():
            vector_score = _cosine_similarity(query_embedding, chunk.embedding or [])
            lexical_content = f"{chunk.normalized_content or ''}\n{chunk.content}"
            score = _hybrid_score(query, lexical_content, vector_score)
            if score >= min_similarity:
                scored.append(_retrieved_from_chunk(chunk, score))
        scored.sort(key=lambda item: item.similarity_score, reverse=True)
        scored = scored[:top_k]
    else:
        # SQLite Python fallback path
        result = await db.execute(stmt)
        for chunk in result.scalars().all():
            vector_score = _cosine_similarity(query_embedding, chunk.embedding or [])
            lexical_content = f"{chunk.normalized_content or ''}\n{chunk.content}"
            score = _hybrid_score(query, lexical_content, vector_score)
            if score >= min_similarity:
                scored.append(_retrieved_from_chunk(chunk, score))

        scored.sort(key=lambda item: item.similarity_score, reverse=True)
        scored = scored[:top_k]

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
