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

from app.repositories.preference_repository import (
    PreferenceRepository
)

from app.schemas.preference import (
    PreferenceUpdate
)


class PreferenceService:

    @staticmethod
    def get_preferences(
        db: Session,
        user: User
    ):

        preference = (
            PreferenceRepository
            .get_by_user_id(
                db,
                user.id
            )
        )

        if not preference:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_404_NOT_FOUND
                ),
                detail=(
                    "Preferences "
                    "not found"
                )
            )

        return preference

    @staticmethod
    def update_preferences(
        db: Session,
        user: User,
        update_data:
        PreferenceUpdate
    ):

        preference = (
            PreferenceRepository
            .get_by_user_id(
                db,
                user.id
            )
        )

        if not preference:
            raise HTTPException(
                status_code=(
                    status
                    .HTTP_404_NOT_FOUND
                ),
                detail=(
                    "Preferences "
                    "not found"
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
                preference,
                key,
                value
            )

        return (
            PreferenceRepository
            .update(
                db,
                preference
            )
        )