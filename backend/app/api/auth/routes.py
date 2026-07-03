from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user_id
from app.database import get_db
from app.schemas.auth import (
    InterestCategoryResponse,
    LoginRequest,
    OnboardingRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    authenticate_user,
    get_all_interests,
    get_user_by_id,
    register_user,
    update_user_onboarding,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(
        db,
        email=request.email,
        password=request.password,
        name=request.name,
        first_name=request.first_name,
        last_name=request.last_name,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    token = authenticate_user(db, request.email, request.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_user_by_id(db, user_id)


@router.get("/interests", response_model=list[InterestCategoryResponse])
def list_interests(db: Session = Depends(get_db)):
    return get_all_interests(db)


@router.patch("/onboarding", response_model=UserResponse)
def onboarding(
    request: OnboardingRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return update_user_onboarding(
        db,
        user_id=user_id,
        grade=request.grade,
        subject=request.subject,
        teaching_style=request.teaching_style,
        answer_format=request.answer_format,
        language=request.preferred_language or request.language,
        interest_ids=request.interest_ids,
        teaching_level=request.teaching_level,
        explanation_method=request.explanation_method,
        learning_modes=[mode.value for mode in request.learning_modes],
        student_interests=[interest.value for interest in request.student_interests],
        goals=request.goals,
        target_exam_date=request.target_exam_date,
    )
