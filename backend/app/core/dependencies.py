"""Reusable FastAPI dependencies."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> int:
    """Read and validate the authenticated user's ID from a JWT bearer token."""
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        return int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid token subject") from exc


def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    """Load the authenticated user row."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    """Protect admin routes.

    If ADMIN_TOKEN is set, that exact bearer token is accepted. Otherwise the
    authenticated user's email must be listed in ADMIN_EMAILS. If neither admin
    mechanism is configured, keep local development permissive but do not treat
    that as production-safe.
    """
    if settings.admin_token and credentials.credentials == settings.admin_token:
        return None
    user_id = get_current_user_id(credentials)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if settings.admin_emails and user.email not in settings.admin_emails:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


def require_configured_admin(user: User | None = Depends(require_admin)) -> User | None:
    """Require explicit admin configuration for sensitive production paths."""
    if not settings.admin_token and not settings.admin_emails:
        raise HTTPException(status_code=403, detail="Set ADMIN_TOKEN or ADMIN_EMAILS to enable admin APIs")
    return user
