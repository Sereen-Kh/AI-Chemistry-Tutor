from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.user import User
from app.models.interest import InterestCategory, UserInterest
from app.core.security import get_password_hash, verify_password, create_access_token


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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_all_interests(db: Session) -> list[InterestCategory]:
    """Return selectable personalization interests ordered for the UI."""
    return db.query(InterestCategory).order_by(InterestCategory.display_order).all()


def update_user_onboarding(
    db: Session,
    user_id: int,
    grade: str,
    teaching_style: str,
    answer_format: str,
    language: str,
    interest_ids: list[int],
) -> User:
    """Persist onboarding preferences and selected interests."""
    user = get_user_by_id(db, user_id)
    user.grade = grade
    user.teaching_style = teaching_style
    user.answer_format = answer_format
    user.language = language

    db.query(UserInterest).filter(UserInterest.user_id == user_id).delete()
    for interest_id in interest_ids:
        exists = db.query(InterestCategory.id).filter(InterestCategory.id == interest_id).first()
        if not exists:
            raise HTTPException(status_code=400, detail=f"Interest ID {interest_id} not found")
        db.add(UserInterest(user_id=user_id, interest_id=interest_id))

    db.commit()
    db.refresh(user)
    return user
