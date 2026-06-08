from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import (
    Session
)

from app.api.dependencies import (
    get_db,
    get_current_user
)

from app.models.user import (
    User
)

from app.schemas.student import (
    StudentProfileUpdate,
    StudentProfileResponse
)

from app.schemas.preference import (
    PreferenceUpdate,
    PreferenceResponse
)

from app.services.student_service import (
    StudentService
)

from app.services.preference_service import (
    PreferenceService
)


router = APIRouter(
    prefix="/students",
    tags=["Students"]
)


# ------------------------
# Student Profile
# ------------------------

@router.get(
    "/me",
    response_model=
    StudentProfileResponse
)
def get_my_profile(
    current_user:
    User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    )
):

    return (
        StudentService
        .get_profile(
            db,
            current_user
        )
    )


@router.patch(
    "/me",
    response_model=
    StudentProfileResponse
)
def update_my_profile(
    update_data:
    StudentProfileUpdate,

    current_user:
    User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    )
):

    return (
        StudentService
        .update_profile(
            db,
            current_user,
            update_data
        )
    )


# ------------------------
# Preferences
# ------------------------

@router.get(
    "/preferences",
    response_model=
    PreferenceResponse
)
def get_preferences(
    current_user:
    User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    )
):

    return (
        PreferenceService
        .get_preferences(
            db,
            current_user
        )
    )


@router.patch(
    "/preferences",
    response_model=
    PreferenceResponse
)
def update_preferences(
    update_data:
    PreferenceUpdate,

    current_user:
    User = Depends(
        get_current_user
    ),

    db: Session = Depends(
        get_db
    )
):

    return (
        PreferenceService
        .update_preferences(
            db,
            current_user,
            update_data
        )
    )