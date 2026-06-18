"""Helpers that prevent scripts from bypassing Alembic migrations."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Engine, inspect, text

DEFAULT_REQUIRED_TABLES = (
    "alembic_version",
    "users",
    "content_sources",
    "rag_chunks",
)


def ensure_migrations_applied(
    engine: Engine,
    *,
    required_tables: Iterable[str] = DEFAULT_REQUIRED_TABLES,
) -> None:
    """Exit clearly if the database schema has not been created by Alembic."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    missing = [table for table in required_tables if table not in existing_tables]
    if missing:
        raise SystemExit(
            "Database schema is not migrated. Missing table(s): "
            f"{', '.join(missing)}. Run `alembic upgrade head` from src/backend before running this script."
        )

    with engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    if not version:
        raise SystemExit(
            "Database is missing an Alembic version stamp. "
            "Run `alembic upgrade head` from src/backend before running this script."
        )
