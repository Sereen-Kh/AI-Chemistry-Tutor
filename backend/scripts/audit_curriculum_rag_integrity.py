#!/usr/bin/env python3
"""Generate read-only curriculum and RAG citation integrity reports."""

from __future__ import annotations

import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal  # noqa: E402
from app.services.curriculum_rag_integrity import write_integrity_reports  # noqa: E402


def main() -> int:
    with SessionLocal() as db:
        paths = write_integrity_reports(db)
    print(json.dumps(paths, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
