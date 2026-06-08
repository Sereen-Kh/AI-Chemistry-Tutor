from datetime import (
    datetime,
    timedelta,
    timezone
)

from jose import (
    JWTError,
    jwt
)

from passlib.context import (
    CryptContext
)

from fastapi import HTTPException
from starlette import status

from app.core.config import settings


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# ----------------------------
# Password Hashing
# ----------------------------

def hash_password(
    password: str
) -> str:
    return pwd_context.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# ----------------------------
# JWT Creation
# ----------------------------

def create_access_token(
    data: dict
) -> str:
    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    to_encode.update(
        {"exp": expire}
    )

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


# ----------------------------
# JWT Decode
# ----------------------------

def decode_access_token(
    token: str
) -> dict:

    credentials_exception = (
        HTTPException(
            status_code=(
                status
                .HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Could not validate "
                "credentials"
            )
        )
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[
                settings.ALGORITHM
            ]
        )

        return payload

    except JWTError:
        raise (
            credentials_exception
        )