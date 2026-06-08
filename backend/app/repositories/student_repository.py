import uuid

from sqlalchemy.orm import Session

from app.models.student_profile import (
    StudentProfile
)


class StudentRepository:

    @staticmethod
    def get_by_user_id(
        db: Session,
        user_id: uuid.UUID
    ) -> StudentProfile | None:

        return (
            db.query(
                StudentProfile
            )
            .filter(
                StudentProfile.user_id
                == user_id
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        profile: StudentProfile
    ) -> StudentProfile:

        db.add(profile)

        db.commit()
        db.refresh(profile)

        return profile

    @staticmethod
    def update(
        db: Session,
        profile: StudentProfile
    ) -> StudentProfile:

        db.commit()

        db.refresh(profile)

        return profile