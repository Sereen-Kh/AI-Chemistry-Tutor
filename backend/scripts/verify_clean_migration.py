#!/usr/bin/env python3
"""Verify Alembic can migrate a clean disposable database from zero state."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import Any

from sqlalchemy import create_engine, inspect, text

from hardening_reports import BACKEND_DIR, bool_env, redact_url, status_line, write_reports

sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402


EXPECTED_TABLES = {
    "users",
    "chapters",
    "lessons",
    "topics",
    "content_sources",
    "rag_chunks",
    "chat_sessions",
    "chat_messages",
    "notifications",
    "interactive_sessions",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify clean Alembic migration.")
    parser.add_argument("--database-url", default=os.getenv("CLEAN_DATABASE_URL") or settings.resolved_database_url)
    parser.add_argument("--allow-non-empty", action="store_true")
    return parser.parse_args()


def _safe_clean_database(url: str) -> bool:
    safe_name_markers = {"migration_test", "clean_test", "ci_test", "edumind_test"}
    return any(marker in url for marker in safe_name_markers)


def _postgres_column_type(conn, table_name: str, column_name: str) -> str | None:
    return conn.execute(
        text(
            """
            SELECT format_type(a.atttypid, a.atttypmod)
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = :table_name
              AND a.attname = :column_name
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY n.nspname = 'public' DESC
            LIMIT 1
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).scalar()


def run() -> int:
    args = parse_args()
    db_url = args.database_url
    errors: list[str] = []
    report: dict[str, Any] = {
        "database_url": redact_url(db_url),
        "migration_command": f"{sys.executable} -m alembic upgrade head",
        "database_considered_disposable": _safe_clean_database(db_url),
        "started_empty": None,
        "migration_returncode": None,
        "migration_head_revision": None,
        "tables_count": 0,
        "expected_tables_present": [],
        "expected_tables_missing": [],
        "pgvector_extension_installed": False,
        "rag_chunks_table_exists": False,
        "embedding_column_exists": False,
        "embedding_column_type": None,
        "errors": errors,
    }
    if not _safe_clean_database(db_url) and not (args.allow_non_empty or bool_env("ALLOW_NON_EMPTY_MIGRATION_TEST")):
        errors.append(
            "Refusing clean migration verification because database URL does not look disposable. "
            "Use CLEAN_DATABASE_URL with a database name containing migration_test, clean_test, ci_test, or edumind_test."
        )
    if errors:
        report["result"] = "failed"
        write_reports(
            report_subdir="smoke",
            report_name="clean_db_migration_report",
            title="Clean DB Migration Verification",
            payload=report,
            sections=[("Errors", [f"- {item}" for item in errors])],
        )
        return 1

    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    if db_url.startswith("postgresql://"):
        env["ASYNC_DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        env["ASYNC_DATABASE_URL"] = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.begin() as conn:
            inspector = inspect(conn)
            initial_tables = set(inspector.get_table_names())
            report["started_empty"] = len(initial_tables) == 0 or initial_tables == {"alembic_version"}
            if not report["started_empty"] and not (args.allow_non_empty or bool_env("ALLOW_NON_EMPTY_MIGRATION_TEST")):
                errors.append(f"Database is not empty before migration: {sorted(initial_tables)}")
                raise RuntimeError(errors[-1])

        completed = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            env=env,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        report["migration_returncode"] = completed.returncode
        if completed.returncode != 0:
            errors.append(
                "alembic upgrade head failed. "
                f"stdout={completed.stdout[-1200:]!r} stderr={completed.stderr[-1200:]!r}"
            )

        with engine.begin() as conn:
            inspector = inspect(conn)
            tables = set(inspector.get_table_names())
            report["tables_count"] = len(tables)
            present = sorted(EXPECTED_TABLES & tables)
            missing = sorted(EXPECTED_TABLES - tables)
            report["expected_tables_present"] = present
            report["expected_tables_missing"] = missing
            report["rag_chunks_table_exists"] = "rag_chunks" in tables
            if missing:
                errors.append(f"Expected tables missing after migration: {missing}")
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            report["migration_head_revision"] = version
            if db_url.startswith(("postgresql://", "postgres://")):
                ext = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname='vector'")).scalar()
                report["pgvector_extension_installed"] = bool(ext)
                if not ext:
                    errors.append("pgvector extension is missing after migration.")
            if "rag_chunks" in tables:
                columns = {column["name"]: column for column in inspector.get_columns("rag_chunks")}
                embedding = columns.get("embedding")
                report["embedding_column_exists"] = embedding is not None
                if embedding and db_url.startswith(("postgresql://", "postgres://")):
                    report["embedding_column_type"] = _postgres_column_type(conn, "rag_chunks", "embedding")
                else:
                    report["embedding_column_type"] = str(embedding["type"]) if embedding else None
                if not embedding:
                    errors.append("rag_chunks.embedding column is missing after migration.")
                elif db_url.startswith(("postgresql://", "postgres://")) and "768" not in str(
                    report["embedding_column_type"]
                ):
                    errors.append(f"rag_chunks.embedding is {report['embedding_column_type']}, expected vector(768).")
    except Exception as exc:
        if not errors:
            errors.append(f"Clean migration verification failed: {type(exc).__name__}: {exc}")

    report["errors"] = errors
    report["result"] = "passed" if not errors else "failed"
    write_reports(
        report_subdir="smoke",
        report_name="clean_db_migration_report",
        title="Clean DB Migration Verification",
        payload=report,
        sections=[
            (
                "Migration",
                [
                    status_line("Database URL", report["database_url"]),
                    status_line("Disposable DB", report["database_considered_disposable"]),
                    status_line("Started empty", report["started_empty"]),
                    status_line("Command", report["migration_command"]),
                    status_line("Return code", report["migration_returncode"]),
                    status_line("Head revision", report["migration_head_revision"]),
                    status_line("Tables count", report["tables_count"]),
                ],
            ),
            (
                "RAG / pgvector",
                [
                    status_line("pgvector installed", report["pgvector_extension_installed"]),
                    status_line("rag_chunks table exists", report["rag_chunks_table_exists"]),
                    status_line("embedding column exists", report["embedding_column_exists"]),
                    status_line("embedding column type", report["embedding_column_type"]),
                ],
            ),
            ("Errors", [f"- {item}" for item in errors] if errors else ["- None"]),
        ],
    )
    for item in errors:
        print(f"ERROR: {item}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(run())
