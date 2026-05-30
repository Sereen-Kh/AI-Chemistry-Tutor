"""Seed interest_categories with default personalization options."""

from __future__ import annotations

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, SessionLocal, engine
import app.models  # noqa: F401
from app.models.interest import InterestCategory

INTEREST_CATEGORIES = [
    {"key": "football", "name_ar": "كرة القدم", "name_en": "Football", "icon": "⚽", "order": 1},
    {"key": "volleyball", "name_ar": "الكرة الطائرة", "name_en": "Volleyball", "icon": "🏐", "order": 2},
    {"key": "cooking", "name_ar": "الطبخ", "name_en": "Cooking", "icon": "🍳", "order": 3},
    {"key": "cycling", "name_ar": "الدراجة", "name_en": "Cycling", "icon": "🚴", "order": 4},
    {"key": "gaming", "name_ar": "الألعاب", "name_en": "Gaming", "icon": "🎮", "order": 5},
    {"key": "music", "name_ar": "الموسيقى", "name_en": "Music", "icon": "🎵", "order": 6},
    {"key": "art", "name_ar": "الفن", "name_en": "Art", "icon": "🎨", "order": 7},
    {"key": "technology", "name_ar": "التكنولوجيا", "name_en": "Technology", "icon": "📱", "order": 8},
    {"key": "nature", "name_ar": "الطبيعة", "name_en": "Nature", "icon": "🌿", "order": 9},
    {"key": "movies", "name_ar": "الأفلام", "name_en": "Movies", "icon": "🎬", "order": 10},
    {"key": "travel", "name_ar": "السفر", "name_en": "Travel", "icon": "✈️", "order": 11},
    {"key": "fitness", "name_ar": "الرياضة", "name_en": "Fitness", "icon": "💪", "order": 12},
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for item in INTEREST_CATEGORIES:
            existing = db.query(InterestCategory).filter(InterestCategory.key == item["key"]).first()
            if existing:
                existing.name_ar = item["name_ar"]
                existing.name_en = item["name_en"]
                existing.icon = item["icon"]
                existing.display_order = item["order"]
            else:
                db.add(
                    InterestCategory(
                        key=item["key"],
                        name_ar=item["name_ar"],
                        name_en=item["name_en"],
                        icon=item["icon"],
                        display_order=item["order"],
                    )
                )
        db.commit()
        print(f"Seeded {len(INTEREST_CATEGORIES)} interest categories.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
