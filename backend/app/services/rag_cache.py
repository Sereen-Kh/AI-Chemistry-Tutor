"""RAG cache invalidation helpers."""

from __future__ import annotations

import logging

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

RAG_CACHE_PATTERNS = (
    "rag_cache:*",
    "semantic_rag:result:*",
    "source_router:*",
)


async def invalidate_rag_caches(patterns: tuple[str, ...] = RAG_CACHE_PATTERNS) -> dict[str, int]:
    """Delete Redis cache keys that can become stale after RAG data changes.

    Best-effort by design: ingestion/re-embedding should not fail just because
    Redis cache invalidation is unavailable.
    """
    redis = get_redis_client()
    deleted: dict[str, int] = {}
    try:
        for pattern in patterns:
            count = 0
            async for key in redis.scan_iter(match=pattern, count=250):
                count += int(await redis.delete(key))
            deleted[pattern] = count
        return deleted
    except Exception as exc:  # pragma: no cover - Redis availability
        logger.warning("RAG cache invalidation failed: %s", exc)
        return deleted
    finally:
        try:
            await redis.aclose()
        except Exception:
            pass
