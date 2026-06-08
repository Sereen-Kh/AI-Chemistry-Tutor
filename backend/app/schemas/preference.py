import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict
)

from app.core.constants import (
    TeachingStyle,
    LearningMode
)


class PreferenceUpdate(
    BaseModel
):
    teaching_style: (
        TeachingStyle | None
    ) = None

    learning_mode: (
        LearningMode | None
    ) = None


class PreferenceResponse(
    BaseModel
):
    id: uuid.UUID
    user_id: uuid.UUID

    teaching_style: (
        TeachingStyle
    )

    learning_mode: (
        LearningMode
    )

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )