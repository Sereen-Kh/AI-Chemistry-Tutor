from fastapi import (
    APIRouter,
    Depends,
    BackgroundTasks
)

from sqlalchemy.orm import (
    Session
)

from fastapi.security import (
    OAuth2PasswordBearer
)

from app.api.dependencies import (
    get_db,
    get_current_user
)

from app.models.user import (
    User
)

from app.schemas.user import (
    UserRegister,
    UserResponse
)

from app.schemas.auth import (
    UserLogin,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest
)

from app.schemas.response import (
    MessageResponse
)

from app.services.auth_service import (
    AuthService
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

oauth2_scheme = (
    OAuth2PasswordBearer(
        tokenUrl="/auth/login"
    )
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201
)
def register(
    user_data: UserRegister,
    db: Session = Depends(
        get_db
    )
):

    return (
        AuthService
        .register(
            db,
            user_data
        )
    )


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    login_data: UserLogin,
    db: Session = Depends(
        get_db
    )
):

    return (
        AuthService
        .login(
            db,
            login_data
        )
    )


@router.get(
    "/me",
    response_model=UserResponse
)
def get_me(
    current_user: User = (
        Depends(
            get_current_user
        )
    )
):

    return current_user


@router.post(
    "/logout",
    response_model=MessageResponse
)
def logout(
    token: str = Depends(
        oauth2_scheme
    ),
    db: Session = Depends(
        get_db
    )
):

    return (
        AuthService
        .logout(
            db,
            token
        )
    )


@router.post(
    "/refresh",
    response_model=TokenResponse
)
def refresh_token(
    current_user: User = (
        Depends(
            get_current_user
        )
    )
):

    return (
        AuthService
        .refresh_token(
            current_user
        )
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse
)
def forgot_password(
    data:
    ForgotPasswordRequest,

    background_tasks:
    BackgroundTasks,

    db: Session = Depends(
        get_db
    )
):

    return (
        AuthService
        .forgot_password(
            db,
            data,
            background_tasks
        )
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse
)
def reset_password(
    data:
    ResetPasswordRequest,

    db: Session = Depends(
        get_db
    )
):

    return (
        AuthService
        .reset_password(
            db,
            data
        )
    )


@router.delete(
    "/account",
    response_model=MessageResponse
)
def delete_account(
    current_user:
    User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    )
):

    return (
        AuthService
        .delete_account(
            db,
            current_user
        )
    )