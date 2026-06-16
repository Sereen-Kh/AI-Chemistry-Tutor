#!/usr/bin/env python3
"""Re-embed stored RAG chunks using the configured embedding provider."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import AsyncSessionLocal  # noqa: E402
from app.services.rag_reembed import reembed_rag_chunks  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate pgvector embeddings for rag_chunks.")
    parser.add_argument("--source-id", type=int, default=None)
    parser.add_argument("--source-type", default=None)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume-failed", action="store_true")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    async with AsyncSessionLocal() as db:
        result = await reembed_rag_chunks(
            db,
            source_id=args.source_id,
            source_type=args.source_type,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            force=args.force,
            resume_failed=args.resume_failed,
        )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
