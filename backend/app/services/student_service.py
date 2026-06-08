from fastapi import (
    HTTPException
)

from sqlalchemy.orm import (
    Session
)

from starlette import (
    status
)

from app.models.user import (
    User
)

from app.repositories.student_repository import (
    StudentRepository
)

from app.schemas.student import (
    StudentProfileUpdate
)


class StudentService:

    @staticmethod
    def get_profile(
        db: Session,
        user: User
    ):

        profile = (
            StudentRepository
            .get_by_user_id(
                db,
                user.id
            )
        )

        if not profile:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_404_NOT_FOUND
                ),
                detail=(
                    "Profile not found"
                )
            )

        return profile

    @staticmethod
    def update_profile(
        db: Session,
        user: User,
        update_data:
        StudentProfileUpdate
    ):

        profile = (
            StudentRepository
            .get_by_user_id(
                db,
                user.id
            )
        )

        if not profile:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Profile not found"
                )
            )

        update_dict = (
            update_data
            .model_dump(
                exclude_unset=True
            )
        )

        for key, value in (
            update_dict.items()
        ):
            setattr(
                profile,
                key,
                value
            )

        return (
            StudentRepository
            .update(
                db,
                profile
            )
        )