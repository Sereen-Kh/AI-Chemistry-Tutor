import hashlib
import secrets
from uuid import UUID
from datetime import (
    datetime,
    timedelta
)

from fastapi import (
    HTTPException,
    BackgroundTasks
)

from sqlalchemy.orm import (
    Session
)

from starlette import status

from app.models.user import User
from app.models.student_profile import (
    StudentProfile
)
from app.models.learning_preference import (
    LearningPreference
)
from app.models.password_reset import (
    PasswordResetToken
)
from app.models.token_blacklist import (
    BlacklistedToken
)

from app.repositories.user_repository import (
    UserRepository
)
from app.repositories.student_repository import (
    StudentRepository
)
from app.repositories.preference_repository import (
    PreferenceRepository
)

from app.schemas.user import (
    UserRegister
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

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)

from app.core.email import (
    send_reset_email
)


class AuthService:

    @staticmethod
    def register(
        db: Session,
        user_data: UserRegister
    ) -> User:

        existing_user = (
            UserRepository
            .get_by_email(
                db,
                user_data.email
            )
        )

        if existing_user:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "Email already exists"
                )
            )

        user = User(
            full_name=(
                user_data.full_name
            ),
            email=user_data.email,
            gender=(
                user_data.gender
            ),
            hashed_password=(
                hash_password(
                    user_data.password
                )
            )
        )

        created_user = (
            UserRepository
            .create(
                db,
                user
            )
        )

        profile = (
            StudentProfile(
                user_id=(
                    created_user.id
                )
            )
        )

        StudentRepository.create(
            db,
            profile
        )

        preference = (
            LearningPreference(
                user_id=(
                    created_user.id
                )
            )
        )

        PreferenceRepository.create(
            db,
            preference
        )

        return created_user

    @staticmethod
    def login(
        db: Session,
        login_data: UserLogin
    ) -> TokenResponse:

        user = (
            UserRepository
            .get_by_email(
                db,
                login_data.email
            )
        )

        if not user:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_401_UNAUTHORIZED
                ),
                detail=(
                    "Invalid credentials"
                )
            )

        valid_password = (
            verify_password(
                login_data.password,
                user.hashed_password
            )
        )

        if not valid_password:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_401_UNAUTHORIZED
                ),
                detail=(
                    "Invalid credentials"
                )
            )

        access_token = (
            create_access_token(
                {
                    "sub":
                    str(user.id)
                }
            )
        )

        return TokenResponse(
            access_token=(
                access_token
            )
        )

    @staticmethod
    def get_current_user(
        db: Session,
        user_id: UUID
    ) -> User:

        user = (
            UserRepository
            .get_by_id(
                db,
                user_id
            )
        )

        if not user:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_404_NOT_FOUND
                ),
                detail="User not found"
            )

        return user

    @staticmethod
    def logout(
        db: Session,
        token: str
    ) -> MessageResponse:

        blacklisted_token = (
            BlacklistedToken(
                token=token
            )
        )

        db.add(
            blacklisted_token
        )

        db.commit()

        return MessageResponse(
            message=(
                "Logout successful"
            )
        )

    @staticmethod
    def refresh_token(
        user: User
    ) -> TokenResponse:

        access_token = (
            create_access_token(
                {
                    "sub":
                    str(user.id)
                }
            )
        )

        return TokenResponse(
            access_token=
            access_token
        )

    @staticmethod
    def forgot_password(
        db: Session,
        data:
        ForgotPasswordRequest,
        background_tasks:
        BackgroundTasks
    ) -> MessageResponse:

        user = (
            UserRepository
            .get_by_email(
                db,
                data.email
            )
        )

        response = (
            MessageResponse(
                message=(
                    "If the email exists, "
                    "a reset link was sent"
                )
            )
        )

        if not user:
            return response

        db.query(
            PasswordResetToken
        ).filter(
            PasswordResetToken
            .user_id
            == user.id
        ).delete()

        reset_token = (
            secrets
            .token_urlsafe(32)
        )

        hashed_token = (
            hashlib.sha256(
                reset_token.encode()
            ).hexdigest()
        )

        expires_at = (
            datetime.utcnow()
            + timedelta(
                minutes=15
            )
        )

        token_entry = (
            PasswordResetToken(
                user_id=user.id,
                token=
                hashed_token,
                expires_at=
                expires_at
            )
        )

        db.add(token_entry)
        db.commit()

        background_tasks.add_task(
            send_reset_email,
            user.email,
            reset_token
        )

        return response

    @staticmethod
    def reset_password(
        db: Session,
        data:
        ResetPasswordRequest
    ) -> MessageResponse:

        hashed_token = (
            hashlib.sha256(
                data.token.encode()
            ).hexdigest()
        )

        token_entry = (
            db.query(
                PasswordResetToken
            )
            .filter(
                PasswordResetToken
                .token
                == hashed_token
            )
            .first()
        )

        if not token_entry:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid reset token"
                )
            )

        if (
            token_entry.expires_at
            < datetime.utcnow()
        ):

            db.delete(
                token_entry
            )

            db.commit()

            raise HTTPException(
                status_code=400,
                detail=(
                    "Reset token expired"
                )
            )

        user = (
            UserRepository
            .get_by_id(
                db,
                token_entry.user_id
            )
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail=(
                    "User not found"
                )
            )

        user.hashed_password = (
            hash_password(
                data.new_password
            )
        )

        db.delete(
            token_entry
        )

        db.commit()

        return MessageResponse(
            message=(
                "Password reset successful"
            )
        )

    @staticmethod
    def delete_account(
        db: Session,
        user: User
    ) -> MessageResponse:

        db.delete(user)
        db.commit()

        return MessageResponse(
            message=(
                "Account deleted "
                "successfully"
            )
        )