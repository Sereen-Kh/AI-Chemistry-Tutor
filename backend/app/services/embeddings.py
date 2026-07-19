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
from app.services.gemini_client import (
    embedding_config,
    get_gemini_client,
    is_gemini_auth_error,
    is_gemini_quota_error,
)

EMBEDDING_DIM = settings.embedding_dimension
logger = logging.getLogger(__name__)
_GEMINI_DISABLED_REASON: str | None = None
_LOCAL_MODEL = None
_LOCAL_MODEL_NAME: str | None = None

GEMINI_EMBEDDING_QUOTA_CODE = "GEMINI_EMBEDDING_QUOTA_EXCEEDED"
GEMINI_EMBEDDING_AUTH_CODE = "GEMINI_EMBEDDING_AUTH_FAILED"
GEMINI_EMBEDDING_PROVIDER_CODE = "GEMINI_EMBEDDING_PROVIDER_FAILED"


class GeminiEmbeddingQuotaError(RuntimeError):
    """Preserve a Gemini quota failure across the provider abstraction."""

    def __init__(self) -> None:
        super().__init__(GEMINI_EMBEDDING_QUOTA_CODE)


class GeminiEmbeddingAuthenticationError(RuntimeError):
    """Preserve a Gemini authentication failure without provider details."""

    def __init__(self) -> None:
        super().__init__(GEMINI_EMBEDDING_AUTH_CODE)


class GeminiEmbeddingProviderError(RuntimeError):
    """Represent a non-quota Gemini failure with a stable safe message."""

    def __init__(self) -> None:
        super().__init__(GEMINI_EMBEDDING_PROVIDER_CODE)


def _raise_terminal_gemini_error(exc: Exception) -> None:
    """Raise stable errors that callers can handle without parsing raw payloads."""

    if is_gemini_quota_error(exc):
        logger.warning("Gemini embedding paused because provider quota was exhausted")
        raise GeminiEmbeddingQuotaError() from exc
    if is_gemini_auth_error(exc):
        logger.warning("Gemini embedding stopped because provider authentication failed")
        raise GeminiEmbeddingAuthenticationError() from exc
    if _provider() == "gemini":
        logger.warning("Gemini embedding provider failed with %s", type(exc).__name__)
        raise GeminiEmbeddingProviderError() from exc


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


def embedding_provider_status() -> dict[str, str | bool | int | None]:
    """Return the currently configured embedding provider for diagnostics."""
    return {
        "provider": _provider(),
        "gemini_model": settings.gemini_embedding_model,
        "local_model": settings.local_embedding_model,
        "embedding_dimension": EMBEDDING_DIM,
        "allow_hash_embeddings": settings.allow_hash_embeddings,
        "allow_local_embeddings": settings.allow_local_embeddings,
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


def current_embedding_model_name() -> str:
    """Return the model identifier that should be stored with chunk embeddings."""
    provider = _provider()
    if provider == "local_multilingual":
        return settings.local_embedding_model
    if provider == "local_hash":
        return "local_hash"
    return settings.gemini_embedding_model


def _hash_embeddings_allowed() -> bool:
    return bool(settings.allow_hash_embeddings)


def _local_embeddings_allowed() -> bool:
    return bool(settings.allow_local_embeddings)


def _raise_embedding_unavailable(reason: str) -> None:
    raise RuntimeError(
        f"Embedding provider unavailable: {reason}. "
        "Production RAG requires GEMINI_EMBEDDING_MODEL=gemini-embedding-001, "
        "EMBEDDING_PROVIDER=gemini, and a valid GEMINI_API_KEY. "
        "Set ALLOW_HASH_EMBEDDINGS=true only in deterministic tests."
    )


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
        if not _hash_embeddings_allowed():
            _raise_embedding_unavailable("local_hash provider is disabled by ALLOW_HASH_EMBEDDINGS=false")
        return _fallback_embedding(text)
    if provider == "local_multilingual":
        if not _local_embeddings_allowed():
            _raise_embedding_unavailable("local_multilingual provider is disabled by ALLOW_LOCAL_EMBEDDINGS=false")
        try:
            return (await asyncio.to_thread(_embed_local_multilingual, [text], task_type))[0]
        except Exception as exc:  # pragma: no cover - optional local model
            if not _hash_embeddings_allowed():
                _raise_embedding_unavailable(str(exc))
            logger.exception("Local multilingual embedding failed; using hash embedding because it is explicitly allowed: %s", exc)
            return _fallback_embedding(text)
    if _should_try_gemini():
        try:
            return await asyncio.to_thread(_embed_gemini_one, text, task_type)
        except Exception as exc:  # pragma: no cover - external API failure
            _raise_terminal_gemini_error(exc)
            _disable_gemini_embeddings(exc)
            logger.warning("Gemini embedding unavailable in auto mode: %s", type(exc).__name__)
    if provider == "gemini":
        if _hash_embeddings_allowed():
            logger.warning("Using hash embedding fallback because ALLOW_HASH_EMBEDDINGS=true")
            return _fallback_embedding(text)
        _raise_embedding_unavailable(_GEMINI_DISABLED_REASON or "Gemini API key/model is not configured")
    if _local_embeddings_allowed():
        try:
            return (await asyncio.to_thread(_embed_local_multilingual, [text], task_type))[0]
        except Exception as exc:  # pragma: no cover - optional local model
            if _hash_embeddings_allowed():
                logger.warning("Local multilingual embedding unavailable; using hash embedding because it is explicitly allowed: %s", exc)
                return _fallback_embedding(text)
            _raise_embedding_unavailable(str(exc))
    if _hash_embeddings_allowed():
        logger.warning("Using hash embedding fallback because ALLOW_HASH_EMBEDDINGS=true")
        return _fallback_embedding(text)
    _raise_embedding_unavailable("Gemini unavailable and local/hash fallbacks are disabled")


def _validate_batch_embeddings(embeddings: list[list[float]], expected_count: int) -> list[list[float]]:
    if len(embeddings) != expected_count:
        raise RuntimeError(f"Embedding provider returned {len(embeddings)} embeddings for {expected_count} texts.")
    bad_dims = sorted({len(item) for item in embeddings if len(item) != EMBEDDING_DIM})
    if bad_dims:
        raise RuntimeError(f"Embedding provider returned dimensions {bad_dims}; expected {EMBEDDING_DIM}.")
    return embeddings


def _validate_embedding(vector: list[float]) -> list[float]:
    if len(vector) != EMBEDDING_DIM:
        raise RuntimeError(f"Embedding provider returned dimension {len(vector)}; expected {EMBEDDING_DIM}.")
    return vector


async def embed_text(text: str) -> list[float]:
    """Embed a document chunk using the configured provider."""
    return _validate_embedding(await _embed_one(text, "RETRIEVAL_DOCUMENT"))


async def embed_document(text: str) -> list[float]:
    """Embed one document chunk using the production document task."""
    return await embed_text(text)


async def embed_query(query: str) -> list[float]:
    """Embed a retrieval query using the query-specific task."""
    return _validate_embedding(await _embed_one(query, "RETRIEVAL_QUERY"))


async def embed_batch(texts: Iterable[str], batch_size: int = 100) -> list[list[float]]:
    """Embed multiple document chunks in batches."""
    items = list(texts)
    if not items:
        return []
    provider = _provider()
    if provider == "local_hash":
        if not _hash_embeddings_allowed():
            _raise_embedding_unavailable("local_hash provider is disabled by ALLOW_HASH_EMBEDDINGS=false")
        return [_fallback_embedding(text) for text in items]

    all_embeddings: list[list[float]] = []
    for index in range(0, len(items), batch_size):
        batch = items[index : index + batch_size]
        if provider == "local_multilingual":
            if not _local_embeddings_allowed():
                _raise_embedding_unavailable("local_multilingual provider is disabled by ALLOW_LOCAL_EMBEDDINGS=false")
            try:
                all_embeddings.extend(
                    _validate_batch_embeddings(
                        await asyncio.to_thread(_embed_local_multilingual, batch, "RETRIEVAL_DOCUMENT"),
                        len(batch),
                    )
                )
                continue
            except Exception as exc:  # pragma: no cover - optional local model
                if not _hash_embeddings_allowed():
                    _raise_embedding_unavailable(str(exc))
                logger.exception(
                    "Local multilingual batch embedding failed; using hash embeddings because it is explicitly allowed: %s",
                    exc,
                )
                all_embeddings.extend(_fallback_embedding(text) for text in batch)
                continue
        if _should_try_gemini():
            try:
                all_embeddings.extend(
                    _validate_batch_embeddings(
                        await asyncio.to_thread(_embed_gemini_batch, batch, "RETRIEVAL_DOCUMENT"),
                        len(batch),
                    )
                )
                continue
            except Exception as exc:  # pragma: no cover - external API failure
                _raise_terminal_gemini_error(exc)
                _disable_gemini_embeddings(exc)
                logger.warning("Gemini batch embedding unavailable in auto mode: %s", type(exc).__name__)
        if provider == "gemini":
            if _hash_embeddings_allowed():
                logger.warning("Using hash embedding fallback because ALLOW_HASH_EMBEDDINGS=true")
                all_embeddings.extend(_fallback_embedding(text) for text in batch)
                continue
            _raise_embedding_unavailable(_GEMINI_DISABLED_REASON or "Gemini API key/model is not configured")
        if _local_embeddings_allowed():
            try:
                all_embeddings.extend(
                    _validate_batch_embeddings(
                        await asyncio.to_thread(_embed_local_multilingual, batch, "RETRIEVAL_DOCUMENT"),
                        len(batch),
                    )
                )
                continue
            except Exception as exc:  # pragma: no cover - optional local model
                if not _hash_embeddings_allowed():
                    _raise_embedding_unavailable(str(exc))
                logger.warning(
                    "Local multilingual embedding unavailable; using hash embeddings because it is explicitly allowed: %s",
                    exc,
                )
        if _hash_embeddings_allowed():
            logger.warning("Using hash embedding fallback because ALLOW_HASH_EMBEDDINGS=true")
            all_embeddings.extend(_fallback_embedding(text) for text in batch)
            continue
        _raise_embedding_unavailable("Gemini unavailable and local/hash fallbacks are disabled")
    return _validate_batch_embeddings(all_embeddings, len(items))


async def embed_documents_batch(texts: list[str], batch_size: int = 50) -> list[list[float]]:
    """Embed document chunks in batches with dimension validation."""
    return await embed_batch(texts, batch_size=batch_size)
