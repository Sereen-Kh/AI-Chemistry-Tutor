"""Compatibility entry point for the canonical reviewed curriculum import.

New operational use should prefer ``scripts/import_reviewed_curriculum.py`` so a
dry-run is performed by default. This legacy command retains its historical apply
behavior while reading only the canonical reviewed catalog.
"""

from __future__ import annotations

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import app.models  # noqa: F401,E402
from app.database import SessionLocal, engine  # noqa: E402
from app.services.curriculum_import import import_reviewed_curriculum  # noqa: E402
from scripts.migration_guard import ensure_migrations_applied  # noqa: E402


def main() -> None:
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
    print(
        "seed_curriculum.py is deprecated; applying the canonical reviewed catalog. "
        "Use import_reviewed_curriculum.py without --apply for a read-only preview."
    )
    with SessionLocal() as db:
        report = import_reviewed_curriculum(db, dry_run=False)
    print(report.model_dump_json(indent=2))
    if report.status == "conflict":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
