from datetime import date
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from app.models.user import User
from app.models.interest import InterestCategory
from app.models.student_profile import StudentProfile
from app.core.security import get_password_hash, verify_password, create_access_token
from app.services.interest_service import (
    get_interest_catalog,
    interest_keys_from_ids,
    sync_user_interests,
    validate_interest_keys,
)
from app.services.preference_mapping import (
    apply_user_preference_updates,
    legacy_teaching_style_from_new,
    normalize_explanation_method,
    normalize_learning_modes,
    normalize_student_interests,
    normalize_teaching_level,
)


def split_name(name: str | None, first_name: str | None, last_name: str | None) -> tuple[str, str]:
    """Resolve old `name` input into first and last name fields."""
    if first_name:
        return first_name.strip(), (last_name or "").strip()
    parts = (name or "").strip().split(maxsplit=1)
    if not parts:
        raise HTTPException(status_code=422, detail="Name is required")
    return parts[0], parts[1] if len(parts) > 1 else ""


def register_user(
    db: Session,
    email: str,
    password: str,
    name: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    """Create a user account and return the persisted user."""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    resolved_first_name, resolved_last_name = split_name(name, first_name, last_name)
    user = User(
        first_name=resolved_first_name,
        last_name=resolved_last_name,
        email=email,
        hashed_password=get_password_hash(password),
    )
    user.student_profile = StudentProfile(
        grade=user.grade,
        subject=user.subject,
        learning_style=user.teaching_style,
        teaching_level=user.teaching_level,
        explanation_method=user.explanation_method,
        learning_modes=user.learning_modes,
        student_interests=user.student_interests,
        preferred_language=user.language,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> str:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return create_access_token(data={"sub": str(user.id)})


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.query(User).options(joinedload(User.student_profile)).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_all_interests(db: Session) -> list[InterestCategory]:
    """Return selectable personalization interests ordered for the UI."""
    return get_interest_catalog(db)


def _raw_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _profile_for_user(db: Session, user: User) -> StudentProfile:
    profile = user.student_profile or db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if profile:
        return profile
    profile = StudentProfile(
        user_id=user.id,
        grade=user.grade,
        subject=user.subject,
        learning_style=user.teaching_style,
        teaching_level=user.teaching_level,
        explanation_method=user.explanation_method,
        learning_modes=user.learning_modes,
        student_interests=user.student_interests,
        preferred_language=user.language,
    )
    db.add(profile)
    user.student_profile = profile
    return profile


def update_user_onboarding(
    db: Session,
    user_id: int,
    grade: str,
    subject: str,
    teaching_style: str,
    answer_format: str,
    language: str,
    interest_ids: list[int],
    teaching_level: str | None = None,
    explanation_method: str | None = None,
    learning_modes: list[str] | None = None,
    student_interests: list[str] | None = None,
    goals: str | None = None,
    target_exam_date: date | None = None,
) -> User:
    """Persist onboarding preferences and selected interests."""
    user = get_user_by_id(db, user_id)
    selected_interest_keys = student_interests or interest_keys_from_ids(db, interest_ids)
    normalized_level = normalize_teaching_level(_raw_value(teaching_level))
    normalized_method = normalize_explanation_method(_raw_value(explanation_method))
    normalized_modes = normalize_learning_modes(learning_modes)
    normalized_interests = normalize_student_interests(validate_interest_keys(selected_interest_keys))

    user.grade = grade
    user.subject = subject
    apply_user_preference_updates(
        user,
        {
            "teaching_style": teaching_style,
            "answer_format": answer_format,
            "teaching_level": normalized_level,
            "explanation_method": normalized_method,
            "learning_modes": normalized_modes,
        },
    )
    user.language = language
    profile = _profile_for_user(db, user)
    profile.grade = grade
    profile.subject = subject
    profile.learning_style = legacy_teaching_style_from_new(normalized_level, normalized_method)
    profile.teaching_level = normalized_level
    profile.explanation_method = normalized_method
    profile.learning_modes = normalized_modes
    profile.preferred_language = language
    profile.goals = goals
    profile.target_exam_date = target_exam_date

    sync_user_interests(
        db,
        user=user,
        profile=profile,
        interest_keys=normalized_interests,
    )

    db.commit()
    db.refresh(user)
    # Keep the relationship present for response serialization.
    user.student_profile = profile
    return user
