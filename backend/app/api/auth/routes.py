from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import register_user, authenticate_user, get_user_by_id
from app.core.security import decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


def _get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> int:
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return int(payload["sub"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, request.name, request.email, request.password)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    token = authenticate_user(db, request.email, request.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(
    user_id: int = Depends(_get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_user_by_id(db, user_id)

