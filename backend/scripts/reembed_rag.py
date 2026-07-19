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
from app.services.rag_reembed import redact_embedding_error, reembed_rag_chunks  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate pgvector embeddings for rag_chunks.")
    parser.add_argument("--source-id", type=int, default=None)
    parser.add_argument("--source-type", default=None)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume-failed", action="store_true")
    parser.add_argument(
        "--resume-after-chunk-id",
        type=int,
        default=None,
        help="Process only candidate rows whose id is greater than this checkpoint.",
    )
    parser.add_argument(
        "--batch-delay-seconds",
        type=float,
        default=0.0,
        help="Wait between provider batches to stay below content-per-minute quotas.",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    def print_progress(payload: dict) -> None:
        processed = int(payload.get("processed") or 0)
        total = int(payload.get("total_candidates") or 0)
        event = {
            "event": "embedding_progress",
            "status": payload.get("status"),
            "progress": payload.get("progress"),
            "processed": processed,
            "total_candidates": total,
            "remaining_candidates": max(0, total - processed),
            "updated": payload.get("updated"),
            "failed": payload.get("failed"),
            "skipped": payload.get("skipped"),
            "batches_completed": payload.get("batches_completed"),
            "retry_count": payload.get("retry_count"),
            "quota_events": payload.get("quota_events"),
            "last_chunk_id": payload.get("last_chunk_id"),
            "stopped_reason": payload.get("stopped_reason"),
            "retry_after_seconds": payload.get("retry_after_seconds"),
            "batch_delay_seconds": payload.get("batch_delay_seconds"),
        }
        print(json.dumps(event, ensure_ascii=False), flush=True)

    try:
        async with AsyncSessionLocal() as db:
            result = await reembed_rag_chunks(
                db,
                source_id=args.source_id,
                source_type=args.source_type,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
                force=args.force,
                resume_failed=args.resume_failed,
                resume_after_chunk_id=args.resume_after_chunk_id,
                batch_delay_seconds=args.batch_delay_seconds,
                progress_callback=print_progress,
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": redact_embedding_error(exc),
                    "resume_after_chunk_id": args.resume_after_chunk_id,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    if result.status == "paused_quota":
        return 2
    return 1 if result.status in {"failed", "completed_with_errors"} else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
