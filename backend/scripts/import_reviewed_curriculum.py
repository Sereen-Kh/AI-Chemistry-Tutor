#!/usr/bin/env python3
"""Dry-run or apply the canonical reviewed curriculum import."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import app.models  # noqa: F401,E402
from app.database import SessionLocal, engine  # noqa: E402
from app.services.curriculum_import import import_reviewed_curriculum  # noqa: E402
from scripts.migration_guard import ensure_migrations_applied  # noqa: E402


DEFAULT_REPORT = BACKEND_DIR.parent / "reports/curriculum/curriculum_import_report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag the command is read-only.",
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_migrations_applied(
        engine,
        required_tables=(
            "alembic_version",
            "units",
            "chapters",
            "lessons",
            "topics",
            "curriculum_entity_mappings",
        ),
    )
    with SessionLocal() as db:
        report = import_reviewed_curriculum(db, dry_run=not args.apply)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(report.model_dump_json(indent=2))
    if report.status == "conflict":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

