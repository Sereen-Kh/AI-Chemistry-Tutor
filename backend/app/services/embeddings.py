"""Embedding helpers for textbook ingestion and RAG retrieval."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from typing import Iterable

from app.core.config import settings
from app.services.gemini_client import embedding_config, get_gemini_client

EMBEDDING_DIM = 768
logger = logging.getLogger(__name__)


def _fallback_embedding(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Create a deterministic token-hash embedding when Gemini credentials are absent."""
    tokens = re.findall(r"[A-Za-z0-9_\u0621-\u064A]+", text.lower())
    vector = [0.0] * dim
    for token in tokens or [text]:
        digest = hashlib.sha256(token.encode("utf-8", errors="ignore")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _embedding_values(response) -> list[list[float]]:
    embeddings = getattr(response, "embeddings", None) or []
    values = [list(item.values or []) for item in embeddings]
    return [item for item in values if item]


async def embed_text(text: str) -> list[float]:
    """Embed a document chunk using the configured Gemini embedding model."""
    if not settings.effective_gemini_api_key:
        return _fallback_embedding(text)

    def _call() -> list[float]:
        client = get_gemini_client()
        result = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=text,
            config=embedding_config("RETRIEVAL_DOCUMENT"),
        )
        embeddings = _embedding_values(result)
        if not embeddings:
            raise RuntimeError("Gemini embedding response did not include vectors.")
        return embeddings[0]

    try:
        return await asyncio.to_thread(_call)
    except Exception as exc:  # pragma: no cover - external API failure
        logger.exception("Gemini document embedding failed; using fallback embedding: %s", exc)
        return _fallback_embedding(text)


async def embed_query(query: str) -> list[float]:
    """Embed a retrieval query using the query-specific embedding task."""
    if not settings.effective_gemini_api_key:
        return _fallback_embedding(query)

    def _call() -> list[float]:
        client = get_gemini_client()
        result = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=query,
            config=embedding_config("RETRIEVAL_QUERY"),
        )
        embeddings = _embedding_values(result)
        if not embeddings:
            raise RuntimeError("Gemini query embedding response did not include vectors.")
        return embeddings[0]

    try:
        return await asyncio.to_thread(_call)
    except Exception as exc:  # pragma: no cover - external API failure
        logger.exception("Gemini query embedding failed; using fallback embedding: %s", exc)
        return _fallback_embedding(query)


async def embed_batch(texts: Iterable[str], batch_size: int = 100) -> list[list[float]]:
    """Embed multiple document chunks in batches."""
    items = list(texts)
    if not items:
        return []
    if not settings.effective_gemini_api_key:
        return [_fallback_embedding(text) for text in items]

    all_embeddings: list[list[float]] = []

    def _embed_batch(batch: list[str]) -> list[list[float]]:
        client = get_gemini_client()
        result = client.models.embed_content(
            model=settings.gemini_embedding_model,
            contents=batch,
            config=embedding_config("RETRIEVAL_DOCUMENT"),
        )
        embeddings = _embedding_values(result)
        if len(embeddings) != len(batch):
            raise RuntimeError(f"Gemini returned {len(embeddings)} embeddings for {len(batch)} texts.")
        return embeddings

    for index in range(0, len(items), batch_size):
        batch = items[index : index + batch_size]
        try:
            all_embeddings.extend(await asyncio.to_thread(_embed_batch, batch))
        except Exception as exc:  # pragma: no cover - external API failure
            logger.exception("Gemini batch embedding failed; using fallback embeddings: %s", exc)
            all_embeddings.extend(_fallback_embedding(text) for text in batch)
    return all_embeddings
