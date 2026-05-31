"""Embedding helpers for textbook ingestion and RAG retrieval."""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
from typing import Iterable

from app.core.config import settings

EMBEDDING_DIM = 768


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


def _configure_genai():
    """Import and configure the Gemini SDK lazily."""
    import google.generativeai as genai

    genai.configure(api_key=settings.effective_gemini_api_key)
    return genai


async def embed_text(text: str) -> list[float]:
    """Embed a document chunk using Google text-embedding-004."""
    if not settings.effective_gemini_api_key:
        return _fallback_embedding(text)

    def _call() -> list[float]:
        genai = _configure_genai()
        result = genai.embed_content(
            model=settings.embedding_model,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]

    return await asyncio.to_thread(_call)


async def embed_query(query: str) -> list[float]:
    """Embed a retrieval query using the query-specific embedding task."""
    if not settings.effective_gemini_api_key:
        return _fallback_embedding(query)

    def _call() -> list[float]:
        genai = _configure_genai()
        result = genai.embed_content(
            model=settings.embedding_model,
            content=query,
            task_type="retrieval_query",
        )
        return result["embedding"]

    return await asyncio.to_thread(_call)


async def embed_batch(texts: Iterable[str], batch_size: int = 100) -> list[list[float]]:
    """Embed multiple document chunks in batches."""
    items = list(texts)
    if not items:
        return []
    if not settings.effective_gemini_api_key:
        return [_fallback_embedding(text) for text in items]

    all_embeddings: list[list[float]] = []

    def _embed_batch(batch: list[str]) -> list[list[float]]:
        genai = _configure_genai()
        result = genai.embed_content(
            model=settings.embedding_model,
            content=batch,
            task_type="retrieval_document",
        )
        embeddings = result["embedding"]
        if embeddings and isinstance(embeddings[0], float):
            return [embeddings]
        return embeddings

    for index in range(0, len(items), batch_size):
        all_embeddings.extend(await asyncio.to_thread(_embed_batch, items[index : index + batch_size]))
    return all_embeddings
