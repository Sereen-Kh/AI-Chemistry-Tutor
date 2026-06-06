"""Embedding helpers for textbook ingestion and RAG retrieval."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
from collections.abc import Sequence
from typing import Iterable

from app.core.config import settings
from app.services.gemini_client import embedding_config, get_gemini_client

EMBEDDING_DIM = 768
logger = logging.getLogger(__name__)
_GEMINI_DISABLED_REASON: str | None = None
_LOCAL_MODEL = None
_LOCAL_MODEL_NAME: str | None = None


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


def _provider() -> str:
    return settings.embedding_provider.strip().lower()


def embedding_provider_status() -> dict[str, str | bool | None]:
    """Return the currently configured embedding provider for diagnostics."""
    return {
        "provider": _provider(),
        "gemini_model": settings.gemini_embedding_model,
        "local_model": settings.local_embedding_model,
        "gemini_disabled": bool(_GEMINI_DISABLED_REASON),
        "gemini_disabled_reason": _GEMINI_DISABLED_REASON,
    }


def _should_try_gemini() -> bool:
    provider = _provider()
    return provider in {"auto", "gemini"} and bool(settings.effective_gemini_api_key) and not _GEMINI_DISABLED_REASON


def _disable_gemini_embeddings(exc: Exception) -> None:
    global _GEMINI_DISABLED_REASON
    if _provider() == "gemini":
        return
    _GEMINI_DISABLED_REASON = f"{type(exc).__name__}: {exc}"


def _e5_texts(texts: Sequence[str], task_type: str) -> list[str]:
    model_name = settings.local_embedding_model.lower()
    if "e5" not in model_name:
        return list(texts)
    prefix = "query: " if task_type == "RETRIEVAL_QUERY" else "passage: "
    return [f"{prefix}{text}" for text in texts]


def _get_local_model():
    """Load an optional sentence-transformers model lazily."""
    global _LOCAL_MODEL, _LOCAL_MODEL_NAME
    model_name = settings.local_embedding_model
    if _LOCAL_MODEL is not None and _LOCAL_MODEL_NAME == model_name:
        return _LOCAL_MODEL
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "sentence-transformers is required for EMBEDDING_PROVIDER=local_multilingual. "
            "Install backend requirements or use EMBEDDING_PROVIDER=local_hash for smoke tests."
        ) from exc

    _LOCAL_MODEL = SentenceTransformer(model_name)
    _LOCAL_MODEL_NAME = model_name
    return _LOCAL_MODEL


def _embed_local_multilingual(texts: Sequence[str], task_type: str) -> list[list[float]]:
    model = _get_local_model()
    encoded = model.encode(
        _e5_texts(texts, task_type),
        normalize_embeddings=True,
        convert_to_numpy=False,
        show_progress_bar=False,
    )
    vectors = [list(map(float, vector)) for vector in encoded]
    bad_dims = {len(vector) for vector in vectors if len(vector) != EMBEDDING_DIM}
    if bad_dims:
        raise RuntimeError(
            f"Local embedding model returned dimensions {sorted(bad_dims)}, but rag_chunks expects {EMBEDDING_DIM}. "
            "Use a 768-dimensional model or migrate the pgvector column dimension."
        )
    return vectors


def _embed_gemini_one(text: str, task_type: str) -> list[float]:
    client = get_gemini_client()
    result = client.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=text,
        config=embedding_config(task_type),
    )
    embeddings = _embedding_values(result)
    if not embeddings:
        raise RuntimeError("Gemini embedding response did not include vectors.")
    return embeddings[0]


def _embed_gemini_batch(texts: Sequence[str], task_type: str) -> list[list[float]]:
    client = get_gemini_client()
    result = client.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=list(texts),
        config=embedding_config(task_type),
    )
    embeddings = _embedding_values(result)
    if len(embeddings) != len(texts):
        raise RuntimeError(f"Gemini returned {len(embeddings)} embeddings for {len(texts)} texts.")
    return embeddings


async def _embed_one(text: str, task_type: str) -> list[float]:
    provider = _provider()
    if provider == "local_hash":
        return _fallback_embedding(text)
    if provider == "local_multilingual":
        try:
            return (await asyncio.to_thread(_embed_local_multilingual, [text], task_type))[0]
        except Exception as exc:  # pragma: no cover - optional local model
            logger.exception("Local multilingual embedding failed; using hash embedding: %s", exc)
            return _fallback_embedding(text)
    if _should_try_gemini():
        try:
            return await asyncio.to_thread(_embed_gemini_one, text, task_type)
        except Exception as exc:  # pragma: no cover - external API failure
            _disable_gemini_embeddings(exc)
            logger.exception("Gemini embedding failed; using local fallback: %s", exc)
    if provider == "gemini":
        return _fallback_embedding(text)
    try:
        return (await asyncio.to_thread(_embed_local_multilingual, [text], task_type))[0]
    except Exception as exc:  # pragma: no cover - optional local model
        logger.warning("Local multilingual embedding unavailable; using hash embedding: %s", exc)
        return _fallback_embedding(text)


async def embed_text(text: str) -> list[float]:
    """Embed a document chunk using the configured provider."""
    return await _embed_one(text, "RETRIEVAL_DOCUMENT")


async def embed_query(query: str) -> list[float]:
    """Embed a retrieval query using the query-specific task."""
    return await _embed_one(query, "RETRIEVAL_QUERY")


async def embed_batch(texts: Iterable[str], batch_size: int = 100) -> list[list[float]]:
    """Embed multiple document chunks in batches."""
    items = list(texts)
    if not items:
        return []
    provider = _provider()
    if provider == "local_hash":
        return [_fallback_embedding(text) for text in items]

    all_embeddings: list[list[float]] = []
    for index in range(0, len(items), batch_size):
        batch = items[index : index + batch_size]
        if provider == "local_multilingual":
            try:
                all_embeddings.extend(await asyncio.to_thread(_embed_local_multilingual, batch, "RETRIEVAL_DOCUMENT"))
                continue
            except Exception as exc:  # pragma: no cover - optional local model
                logger.exception("Local multilingual batch embedding failed; using hash embeddings: %s", exc)
                all_embeddings.extend(_fallback_embedding(text) for text in batch)
                continue
        if _should_try_gemini():
            try:
                all_embeddings.extend(await asyncio.to_thread(_embed_gemini_batch, batch, "RETRIEVAL_DOCUMENT"))
                continue
            except Exception as exc:  # pragma: no cover - external API failure
                _disable_gemini_embeddings(exc)
                logger.exception("Gemini batch embedding failed; using local fallback: %s", exc)
        if provider == "gemini":
            all_embeddings.extend(_fallback_embedding(text) for text in batch)
            continue
        try:
            all_embeddings.extend(await asyncio.to_thread(_embed_local_multilingual, batch, "RETRIEVAL_DOCUMENT"))
        except Exception as exc:  # pragma: no cover - optional local model
            logger.warning("Local multilingual embedding unavailable; using hash embeddings: %s", exc)
            all_embeddings.extend(_fallback_embedding(text) for text in batch)
    return all_embeddings
