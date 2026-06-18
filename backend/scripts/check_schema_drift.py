"""Check that Alembic head creates all model tables and columns.

This script uses a disposable SQLite database so it never mutates developer or
production data. It is intentionally focused on table/column presence; index
and constraint parity can be added later once all historical migrations are
fully normalized across SQLite and PostgreSQL.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import app.models  # noqa: E402,F401
from app.database import Base  # noqa: E402


def _model_schema() -> dict[str, set[str]]:
    return {
        table_name: {column.name for column in table.columns}
        for table_name, table in Base.metadata.tables.items()
    }


def _database_schema(database_url: str) -> dict[str, set[str]]:
    engine = create_engine(database_url)
    inspector = inspect(engine)
    return {
        table_name: {column["name"] for column in inspector.get_columns(table_name)}
        for table_name in inspector.get_table_names()
        if table_name != "alembic_version"
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="edumind_schema_drift_") as tmp_dir:
        db_path = Path(tmp_dir) / "schema.db"
        database_url = f"sqlite:///{db_path}"
        env = {
            **os.environ,
            "DATABASE_URL": database_url,
            "ASYNC_DATABASE_URL": database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1),
        }
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if migration.returncode != 0:
            print(migration.stdout)
            print(migration.stderr, file=sys.stderr)
            return migration.returncode

        expected = _model_schema()
        actual = _database_schema(database_url)

    missing_tables = sorted(set(expected) - set(actual))
    extra_tables = sorted(set(actual) - set(expected))
    missing_columns = {
        table: sorted(expected[table] - actual.get(table, set()))
        for table in sorted(expected)
        if expected[table] - actual.get(table, set())
    }
    extra_columns = {
        table: sorted(actual[table] - expected.get(table, set()))
        for table in sorted(actual)
        if actual[table] - expected.get(table, set())
    }
    report = {
        "missing_tables": missing_tables,
        "extra_tables": extra_tables,
        "missing_columns": missing_columns,
        "extra_columns": extra_columns,
        "status": "passed" if not (missing_tables or extra_tables or missing_columns or extra_columns) else "failed",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
