"""Smoke-test the semantic RAG pipeline over PostgreSQL/pgvector."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys
import time

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.redis import close_redis_pool  # noqa: E402
from app.database import AsyncSessionLocal  # noqa: E402
from app.services.semantic_rag import semantic_retrieve_context  # noqa: E402


DEFAULT_QUERIES = [
    "ما هي الحموض؟",
    "ما هو الجدول الدوري؟",
    "احسب عدد أيونات H+ في HCl و H2SO4 و H3PO4 من كتاب الحلول صفحة 117",
    "اشرح الحموض ثم حل مثال عن حمض كلور الماء HCl",
]


def _snippet(text: str, limit: int = 180) -> str:
    return " ".join((text or "").split())[:limit]


async def run_query(query: str, top_k: int) -> None:
    started = time.monotonic()
    async with AsyncSessionLocal() as db:
        result = await semantic_retrieve_context(db, query, top_k=top_k)
    latency_ms = int((time.monotonic() - started) * 1000)
    diagnostics = result.diagnostics
    source_route = diagnostics.get("source_route") or {}

    print("\n" + "=" * 96)
    print(f"Query: {query}")
    print(f"Route: {source_route.get('route')} -> {source_route.get('source_types')}")
    print(f"Route reason: {source_route.get('reason')} | matched={source_route.get('matched_terms')}")
    print(f"Rewritten: {diagnostics.get('rewritten_query')}")
    print(f"Multi-query: {diagnostics.get('multi_queries')}")
    print(
        "Fusion: "
        f"variants={diagnostics.get('variant_count')} "
        f"candidates={diagnostics.get('fused_candidate_count')} "
        f"reranker={diagnostics.get('reranker_model')} used={diagnostics.get('reranker_used')} "
        f"latency_ms={latency_ms}"
    )
    print("Top chunks:")
    for index, chunk in enumerate(result.chunks, start=1):
        print(
            f"{index}. score={chunk.similarity_score:.4f} "
            f"source={chunk.source_type} page={chunk.page_number} "
            f"type={chunk.content_type} chunk_id={chunk.id}"
        )
        print(f"   {_snippet(chunk.content)}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test semantic RAG source routing and retrieval.")
    parser.add_argument("--query", action="append", help="Query to test. Can be repeated.")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    queries = args.query or DEFAULT_QUERIES
    try:
        for query in queries:
            await run_query(query, args.top_k)
    finally:
        await close_redis_pool()


if __name__ == "__main__":
    asyncio.run(main())
