#!/usr/bin/env python3
"""Invalidate all versioned RAG caches during activation or rollback."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.rag_cache import invalidate_rag_caches  # noqa: E402


async def main() -> None:
    print(json.dumps(await invalidate_rag_caches(), indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
