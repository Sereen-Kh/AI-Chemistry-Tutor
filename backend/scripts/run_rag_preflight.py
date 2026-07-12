#!/usr/bin/env python3
"""Print the read-only production RAG preflight baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.services.rag_preflight import build_rag_preflight  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the read-only RAG production preflight.")
    parser.add_argument("--json", action="store_true", help="Print the complete JSON response.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with SessionLocal() as db:
        payload = build_rag_preflight(db)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        database = payload["database"]
        chunks = payload["chunks"]
        print("RAG PRODUCTION PREFLIGHT")
        print(f"status: {payload['status']}")
        print(f"database: {database['dialect']} (reachable={database['reachable']})")
        print(f"pgvector: {database['pgvector_version'] or 'unavailable'}")
        print(f"reviewed metadata ready: {payload['reviewed_metadata']['ready_for_embedding']}")
        print(f"reviewed chunks: {chunks['reviewed_chunks_total']}")
        print(f"database chunks: {chunks['database_chunks_total']}")
        print(f"completed embeddings: {chunks['completed_embeddings']}")
        print(f"can load chunks: {payload['can_load_chunks']}")
        print(f"can embed: {payload['can_embed']}")
        print(f"can evaluate: {payload['can_evaluate']}")
        if payload["blocking_issues"]:
            print("blocking issues: " + ", ".join(payload["blocking_issues"]))
        if payload["warnings"]:
            print("warnings: " + ", ".join(payload["warnings"]))
    return 0 if payload["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())

