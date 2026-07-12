"""Read-only admin curriculum diagnostics."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import get_db
from app.schemas.curriculum_readiness import CurriculumReadinessResponse
from app.services.curriculum_readiness import validate_curriculum_readiness


router = APIRouter(prefix="/admin/curriculum", tags=["admin-curriculum"])


@router.get("/readiness", response_model=CurriculumReadinessResponse)
def get_curriculum_readiness(
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
) -> CurriculumReadinessResponse:
    """Report current curriculum defects without mutating curriculum rows."""

    return validate_curriculum_readiness(db)

