from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict
from app.core.constants import LearningMode, TeachingStyle
from app.core.constants import PreferredLanguage


class StudentProfileUpdate(
    BaseModel
):
    grade: int | None = None

    preferred_language: (
        PreferredLanguage | None
    ) = None

    avatar_url: str | None = None

    onboarding_completed: (
        bool | None
    ) = None


class StudentProfileResponse(
    BaseModel
):
    id: uuid.UUID
    user_id: uuid.UUID

    grade: int

    preferred_language: (
        PreferredLanguage
    )
    learning_mode: LearningMode | None = None
    teaching_style: TeachingStyle | None = None

    avatar_url: str | None

    onboarding_completed: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )