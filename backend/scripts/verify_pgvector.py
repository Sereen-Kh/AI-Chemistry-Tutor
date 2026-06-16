#!/usr/bin/env python3
"""Verify PostgreSQL pgvector readiness without modifying production tables."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from sqlalchemy import create_engine, inspect, text

from hardening_reports import BACKEND_DIR, redact_url, status_line, write_reports

sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify pgvector for EduMind RAG.")
    parser.add_argument("--database-url", default=settings.resolved_database_url)
    return parser.parse_args()


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
    report: dict[str, Any] = {
        "database_url": redact_url(args.database_url),
        "postgres_reachable": False,
        "pgvector_extension_installed": False,
        "pgvector_extension_version": None,
        "rag_chunks_table_exists": False,
        "embedding_column_exists": False,
        "embedding_column_type": None,
        "embedding_dimension_768": False,
        "embedding_index_exists": False,
        "similarity_operator_works": False,
        "errors": [],
    }
    errors: list[str] = []
    if not args.database_url.startswith(("postgresql://", "postgres://")):
        errors.append("pgvector verification requires a PostgreSQL database URL.")
        report["errors"] = errors
        report["result"] = "failed"
        write_reports(
            report_subdir="smoke",
            report_name="pgvector_report",
            title="pgvector Verification",
            payload=report,
            sections=[("Errors", [f"- {item}" for item in errors])],
        )
        return 1

    try:
        engine = create_engine(args.database_url, pool_pre_ping=True)
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
            report["postgres_reachable"] = True
            ext = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            ).scalar()
            report["pgvector_extension_installed"] = bool(ext)
            report["pgvector_extension_version"] = ext
            if not ext:
                errors.append("pgvector extension is not installed.")

            inspector = inspect(conn)
            tables = set(inspector.get_table_names())
            report["rag_chunks_table_exists"] = "rag_chunks" in tables
            if "rag_chunks" not in tables:
                errors.append("rag_chunks table is missing.")
            else:
                columns = {column["name"]: column for column in inspector.get_columns("rag_chunks")}
                embedding = columns.get("embedding")
                report["embedding_column_exists"] = embedding is not None
                if not embedding:
                    errors.append("rag_chunks.embedding column is missing.")
                else:
                    coltype = _postgres_column_type(conn, "rag_chunks", "embedding") or str(embedding["type"])
                    report["embedding_column_type"] = coltype
                    report["embedding_dimension_768"] = "768" in coltype
                    if "768" not in coltype:
                        errors.append(f"rag_chunks.embedding is {coltype}, expected vector(768).")
                indexes = inspector.get_indexes("rag_chunks")
                report["embedding_index_exists"] = any(
                    "embedding" in " ".join(index.get("column_names") or [])
                    or "embedding" in str(index.get("name", ""))
                    for index in indexes
                )

            if ext:
                conn.execute(text("CREATE TEMP TABLE edumind_pgvector_smoke (id integer, embedding vector(3))"))
                conn.execute(
                    text(
                        "INSERT INTO edumind_pgvector_smoke (id, embedding) "
                        "VALUES (1, '[1,0,0]'), (2, '[0,1,0]')"
                    )
                )
                nearest = conn.execute(
                    text(
                        "SELECT id FROM edumind_pgvector_smoke "
                        "ORDER BY embedding <=> '[1,0,0]' LIMIT 1"
                    )
                ).scalar()
                report["similarity_operator_works"] = nearest == 1
                if nearest != 1:
                    errors.append("pgvector cosine/distance operator returned an unexpected result.")
    except Exception as exc:
        errors.append(f"pgvector verification failed: {type(exc).__name__}: {exc}")

    report["errors"] = errors
    report["result"] = "passed" if not errors else "failed"
    write_reports(
        report_subdir="smoke",
        report_name="pgvector_report",
        title="pgvector Verification",
        payload=report,
        sections=[
            (
                "Checks",
                [
                    status_line("Database URL", report["database_url"]),
                    status_line("PostgreSQL reachable", report["postgres_reachable"]),
                    status_line("pgvector installed", report["pgvector_extension_installed"]),
                    status_line("pgvector version", report["pgvector_extension_version"]),
                    status_line("rag_chunks exists", report["rag_chunks_table_exists"]),
                    status_line("embedding column exists", report["embedding_column_exists"]),
                    status_line("embedding column type", report["embedding_column_type"]),
                    status_line("embedding dimension 768", report["embedding_dimension_768"]),
                    status_line("embedding index exists", report["embedding_index_exists"]),
                    status_line("similarity operator works", report["similarity_operator_works"]),
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
