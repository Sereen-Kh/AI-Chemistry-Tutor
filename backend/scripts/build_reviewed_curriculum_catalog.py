#!/usr/bin/env python3
"""Build the canonical reviewed Grade 9 Chemistry curriculum catalog."""

from __future__ import annotations

from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.reviewed_curriculum_catalog import (  # noqa: E402
    build_reviewed_curriculum_catalog,
    write_reviewed_curriculum_catalog,
)


def main() -> None:
    catalog = build_reviewed_curriculum_catalog()
    path = write_reviewed_curriculum_catalog(catalog)
    lesson_count = sum(
        len(chapter.lessons)
        for unit in catalog.units
        for chapter in unit.chapters
    )
    topic_count = sum(
        len(lesson.topics)
        for unit in catalog.units
        for chapter in unit.chapters
        for lesson in chapter.lessons
    )
    print(f"catalog: {path}")
    print(f"units: {len(catalog.units)}")
    print(f"lessons: {lesson_count}")
    print(f"topics: {topic_count}")
    print(f"reviewed metadata version: {catalog.reviewed_metadata_version}")


if __name__ == "__main__":
    main()

