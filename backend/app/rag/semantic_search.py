"""CLI entrypoint for semantic RAG search.

Run from ``backend``:

    python -m app.rag.semantic_search --query "حل مسألة التركيز المولي" --source-types solution_book
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.database import AsyncSessionLocal
from app.services.semantic_rag import semantic_search


def _parse_source_types(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run semantic RAG search.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--source-types", default=None, help="Comma-separated source types, e.g. solution_book,textbook.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--mode",
        choices=["textbook_first", "solution_first", "balanced", "solution_only", "textbook_only"],
        default="balanced",
    )
    parser.add_argument("--min-similarity", type=float, default=0.45)
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    async with AsyncSessionLocal() as db:
        results, diagnostics = await semantic_search(
            db,
            query=args.query,
            source_types=_parse_source_types(args.source_types),
            top_k=args.top_k,
            mode=args.mode,
            min_similarity=args.min_similarity,
        )
    print(
        json.dumps(
            {
                "query": args.query,
                "diagnostics": diagnostics,
                "results": [result.__dict__ for result in results],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main(sys.argv[1:])
