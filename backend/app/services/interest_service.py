"""Canonical interest catalog validation and user-selection persistence."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.enums import StudentInterest
from app.models.interest import InterestCategory, UserInterest
from app.models.student_profile import StudentProfile
from app.models.user import User

MIN_INTERESTS = 1
MAX_INTERESTS = 3

INTEREST_CATALOG = (
    {"key": "daily_life", "name_ar": "الحياة اليومية", "name_en": "Daily life", "icon": "house", "display_order": 10},
    {"key": "laboratory", "name_ar": "المختبر", "name_en": "Laboratory", "icon": "flask-conical", "display_order": 20},
    {"key": "nature", "name_ar": "الطبيعة", "name_en": "Nature", "icon": "leaf", "display_order": 30},
    {"key": "football", "name_ar": "كرة القدم", "name_en": "Football", "icon": "trophy", "display_order": 40},
    {"key": "cars", "name_ar": "السيارات", "name_en": "Cars", "icon": "car", "display_order": 50},
    {"key": "cooking", "name_ar": "الطبخ", "name_en": "Cooking", "icon": "cooking-pot", "display_order": 60},
    {"key": "gaming", "name_ar": "الألعاب", "name_en": "Gaming", "icon": "gamepad-2", "display_order": 70},
)

ALLOWED_INTEREST_KEYS = frozenset(
    interest.value for interest in StudentInterest if interest is not StudentInterest.NONE
)

ERROR_MESSAGES = {
    "INTEREST_REQUIRED": "اختر اهتماماً واحداً على الأقل.",
    "TOO_MANY_INTERESTS": "يمكنك اختيار ثلاثة اهتمامات كحد أقصى.",
    "INVALID_INTEREST": "يتضمن الاختيار اهتماماً غير صالح.",
    "DUPLICATE_INTEREST": "لا يمكن تكرار الاهتمام نفسه.",
}


def _interest_error(code: str, *, value: Any = None) -> HTTPException:
    detail: dict[str, Any] = {"code": code, "message": ERROR_MESSAGES[code]}
    if value is not None:
        detail["value"] = value
    return HTTPException(status_code=422, detail=detail)


def _key(value: object) -> str:
    return str(getattr(value, "value", value)).strip()


def validate_interest_keys(values: Iterable[object] | None, *, required: bool = True) -> list[str]:
    """Validate the stable interest-key contract without silently repairing input."""

    keys = [_key(value) for value in values or []]
    if len(keys) != len(set(keys)):
        raise _interest_error("DUPLICATE_INTEREST")
    if required and len(keys) < MIN_INTERESTS:
        raise _interest_error("INTEREST_REQUIRED")
    if len(keys) > MAX_INTERESTS:
        raise _interest_error("TOO_MANY_INTERESTS")
    invalid = next((key for key in keys if key not in ALLOWED_INTEREST_KEYS), None)
    if invalid is not None:
        raise _interest_error("INVALID_INTEREST", value=invalid)
    return keys


def get_interest_catalog(db: Session) -> list[InterestCategory]:
    """Read the migration-seeded catalog without mutating state."""

    return db.query(InterestCategory).order_by(InterestCategory.display_order).all()


def interest_keys_from_ids(db: Session, interest_ids: Iterable[int]) -> list[str]:
    ids = list(interest_ids)
    if len(ids) != len(set(ids)):
        raise _interest_error("DUPLICATE_INTEREST")
    if not ids:
        return []
    interests = db.query(InterestCategory).filter(InterestCategory.id.in_(ids)).all()
    by_id = {interest.id: interest for interest in interests}
    missing = next((interest_id for interest_id in ids if interest_id not in by_id), None)
    if missing is not None:
        raise _interest_error("INVALID_INTEREST", value=missing)
    ordered = sorted((by_id[interest_id] for interest_id in ids), key=lambda item: item.display_order)
    return [interest.key for interest in ordered]


def _resolve_categories(db: Session, keys: list[str]) -> list[InterestCategory]:
    categories = db.query(InterestCategory).filter(InterestCategory.key.in_(keys)).all()
    by_key = {category.key: category for category in categories}
    missing = next((key for key in keys if key not in by_key), None)
    if missing is not None:
        raise _interest_error("INVALID_INTEREST", value=missing)
    return [by_key[key] for key in keys]


def sync_user_interests(
    db: Session,
    *,
    user: User,
    profile: StudentProfile,
    interest_keys: Iterable[object],
) -> list[str]:
    """Persist canonical join rows and compatibility JSON fields atomically."""

    keys = validate_interest_keys(interest_keys)
    categories = _resolve_categories(db, keys)
    db.query(UserInterest).filter(UserInterest.user_id == user.id).delete()
    db.add_all(UserInterest(user_id=user.id, interest_id=category.id) for category in categories)
    user.student_interests = keys
    profile.student_interests = keys
    return keys


async def sync_user_interests_async(
    db: AsyncSession,
    *,
    user: User,
    profile: StudentProfile,
    interest_keys: Iterable[object],
) -> list[str]:
    """Async equivalent used by profile and user preference endpoints."""

    keys = validate_interest_keys(interest_keys)
    result = await db.execute(select(InterestCategory).where(InterestCategory.key.in_(keys)))
    by_key = {category.key: category for category in result.scalars()}
    missing = next((key for key in keys if key not in by_key), None)
    if missing is not None:
        raise _interest_error("INVALID_INTEREST", value=missing)
    await db.execute(delete(UserInterest).where(UserInterest.user_id == user.id))
    db.add_all(UserInterest(user_id=user.id, interest_id=by_key[key].id) for key in keys)
    user.student_interests = keys
    profile.student_interests = keys
    return keys
