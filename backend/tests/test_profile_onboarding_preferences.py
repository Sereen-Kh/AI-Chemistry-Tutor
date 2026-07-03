"""Profile/onboarding preference ownership tests."""

from __future__ import annotations

import asyncio

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.auth_service import get_all_interests, register_user, update_user_onboarding
from app.services.onboarding_service import is_user_onboarding_complete
from app.services.profile_service import upsert_profile


def test_onboarding_saves_canonical_profile_and_legacy_user_fields() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        user = register_user(db, email="new@example.com", password="123456789", first_name="سارة")
        assert is_user_onboarding_complete(user) is False

        interests = get_all_interests(db)
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
                },
            )
            refreshed = await db.get(User, user.id)

            assert profile.onboarding_completed is True
            assert refreshed is not None
            assert refreshed.teaching_level == "academic"
            assert refreshed.explanation_method == "exam_mode"
            assert refreshed.learning_modes == ["text", "image"]
            assert refreshed.student_interests == ["cars"]
        await engine.dispose()

    asyncio.run(scenario())
