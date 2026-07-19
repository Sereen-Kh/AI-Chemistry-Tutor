"""Profile/onboarding preference ownership tests."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.interest import InterestCategory, UserInterest
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.auth_service import get_all_interests, register_user, update_user_onboarding
from app.services.interest_service import INTEREST_CATALOG, validate_interest_keys
from app.services.onboarding_service import is_user_onboarding_complete
from app.services.profile_service import upsert_profile


def _seed_interests(db) -> list[InterestCategory]:
    interests = [InterestCategory(**payload) for payload in INTEREST_CATALOG]
    db.add_all(interests)
    db.commit()
    return get_all_interests(db)


def test_interest_catalog_read_does_not_seed_missing_rows() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        assert get_all_interests(db) == []
        assert db.query(InterestCategory).count() == 0
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ([], "INTEREST_REQUIRED"),
        (["cars", "cars"], "DUPLICATE_INTEREST"),
        (["cars", "laboratory", "nature", "gaming"], "TOO_MANY_INTERESTS"),
        (["unknown"], "INVALID_INTEREST"),
    ],
)
def test_interest_selection_validation_returns_stable_codes(values: list[str], code: str) -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_interest_keys(values)
    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == code


def test_onboarding_saves_canonical_profile_and_legacy_user_fields() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        user = register_user(db, email="new@example.com", password="123456789", first_name="سارة")
        assert is_user_onboarding_complete(user) is False

        interests = _seed_interests(db)
        selected_ids = [interests[0].id, interests[1].id]
        updated = update_user_onboarding(
            db,
            user_id=user.id,
            grade="grade_9",
            subject="chemistry",
            teaching_style="step_by_step",
            answer_format="text",
            language="ar",
            interest_ids=selected_ids,
            teaching_level="simple",
            explanation_method="step_by_step",
            learning_modes=["text", "audio"],
            student_interests=[interests[0].key, interests[1].key],
            goals="تقوية مسائل التركيز",
        )

        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).one()
        assert updated.onboarding_completed is True
        assert profile.onboarding_completed is True
        assert profile.teaching_level == "simple"
        assert profile.explanation_method == "step_by_step"
        assert profile.learning_modes == ["text", "audio"]
        assert profile.student_interests == [interests[0].key, interests[1].key]
        assert profile.goals == "تقوية مسائل التركيز"
        assert updated.teaching_level == profile.teaching_level
        assert updated.learning_modes == profile.learning_modes
        links = db.query(UserInterest).filter(UserInterest.user_id == user.id).all()
        assert {link.interest_id for link in links} == set(selected_ids)

        update_user_onboarding(
            db,
            user_id=user.id,
            grade="grade_9",
            subject="chemistry",
            teaching_style="step_by_step",
            answer_format="text",
            language="ar",
            interest_ids=[],
            student_interests=[interests[0].key, interests[1].key],
        )
        assert db.query(UserInterest).filter(UserInterest.user_id == user.id).count() == 2
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_student_profile_update_mirrors_legacy_user_for_chat_preferences() -> None:
    async def scenario() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
        async with SessionLocal() as db:
            user = User(first_name="علي", last_name="", email="ali@example.com", hashed_password="hashed")
            db.add(user)
            db.add(InterestCategory(**INTEREST_CATALOG[4]))
            await db.commit()
            await db.refresh(user)

            profile = await upsert_profile(
                db,
                user.id,
                {
                    "grade": "grade_9",
                    "subject": "chemistry",
                    "teaching_level": "academic",
                    "explanation_method": "exam_mode",
                    "learning_modes": ["text", "image"],
                    "student_interests": ["cars"],
                    "preferred_language": "ar",
                    "goals": "الاستعداد للامتحان",
                    "learning_memory_enabled": False,
                },
            )
            refreshed = await db.get(User, user.id)

            assert profile.onboarding_completed is True
            assert refreshed is not None
            assert refreshed.teaching_level == "academic"
            assert refreshed.explanation_method == "exam_mode"
            assert refreshed.learning_modes == ["text", "image"]
            assert refreshed.student_interests == ["cars"]
            assert profile.learning_memory_enabled is False
            assert profile.metadata_json == {"learning_memory_enabled": False}
        await engine.dispose()

    asyncio.run(scenario())
