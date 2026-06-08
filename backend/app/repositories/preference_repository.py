import uuid

from sqlalchemy.orm import Session

from app.models.learning_preference import (
    LearningPreference
)


class PreferenceRepository:

    @staticmethod
    def get_by_user_id(
        db: Session,
        user_id: uuid.UUID
    ) -> (
        LearningPreference
        | None
    ):

        return (
            db.query(
                LearningPreference
            )
            .filter(
                LearningPreference
                .user_id
                == user_id
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        preference:
        LearningPreference
    ) -> (
        LearningPreference
    ):

        db.add(preference)

        db.commit()

        db.refresh(
            preference
        )

        return preference

    @staticmethod
    def update(
        db: Session,
        preference:
        LearningPreference
    ) -> (
        LearningPreference
    ):

        db.commit()

        db.refresh(
            preference
        )

        return preference