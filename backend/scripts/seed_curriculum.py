"""Seed chapters and lessons tables in chemistry database using book_structure.json."""

from __future__ import annotations

import json
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine
import app.models
from app.models.chemistry import Chapter, Lesson


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        book_structure_path = PROJECT_DIR / "data" / "textbooks" / "syria_grade_9_chemistry" / "book_structure.json"
        if not book_structure_path.exists():
            print(f"Error: book_structure.json not found at {book_structure_path}")
            sys.exit(1)

        structure = json.loads(book_structure_path.read_text(encoding="utf-8"))
        unit_title = structure.get("unit") or "الكيمياء اللاعضوية والكيمياء العضوية"

        # Check or create Chapter
        chapter = db.query(Chapter).filter(Chapter.title_ar == unit_title).first()
        if not chapter:
            chapter = Chapter(
                title_ar=unit_title,
                title_en="Inorganic and Organic Chemistry",
                description_ar="الوحدة الرابعة من كتاب الكيمياء للصف التاسع في سوريا",
                order=1,
                difficulty=2,
                icon="🧪",
            )
            db.add(chapter)
            db.commit()
            db.refresh(chapter)
            print(f"Created Chapter: {unit_title} (ID: {chapter.id})")
        else:
            print(f"Using existing Chapter: {unit_title} (ID: {chapter.id})")

        # Check or create Lessons
        lessons_data = structure.get("lessons") or []
        for item in lessons_data:
            lesson_no = item.get("lesson_no")
            title = item.get("title")
            
            # Simple content summary from objectives
            objectives = item.get("objectives") or []
            content_ar = "الأهداف:\n" + "\n".join(f"- {obj}" for obj in objectives)

            lesson = db.query(Lesson).filter(
                Lesson.chapter_id == chapter.id,
                Lesson.order == lesson_no
            ).first()

            if not lesson:
                # also check by title to be safe
                lesson = db.query(Lesson).filter(
                    Lesson.chapter_id == chapter.id,
                    Lesson.title_ar == title
                ).first()

            if lesson:
                lesson.title_ar = title
                lesson.order = lesson_no
                lesson.content_ar = content_ar
                print(f"Updated Lesson {lesson_no}: {title} (ID: {lesson.id})")
            else:
                lesson = Lesson(
                    chapter_id=chapter.id,
                    title_ar=title,
                    content_ar=content_ar,
                    order=lesson_no,
                    difficulty=2,
                    duration_min=45,
                )
                db.add(lesson)
                print(f"Added Lesson {lesson_no}: {title}")

        db.commit()
        print("Curriculum seeding completed successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
