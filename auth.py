import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from models import User

# Initialize with recommended Argon2 settings
password_hash = PasswordHash.recommended()
# Initialize oauth2 password bearer scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/token")
settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password"""
    return password_hash.hash(password)


def verify_password(password: str, hased_password: str) -> bool:
    """Verify a password"""
    return password_hash.verify(password, hased_password)


def generate_reset_password_token() -> str:
    """Generates a cryptographically secure random string"""
    return secrets.token_urlsafe(32)


def hash_reset_password_token(token: str) -> str:
    """Converts a token into a fixed-length SHA-256 hash string"""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_access_token(
    subject: str,
    extra_claims: dict | None = None,
    expire_delta: timedelta | None = None,
) -> str:
    """Generate a signed JWT access token."""
    now = datetime.now(UTC)
    lifetime = expire_delta or timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    claims = {
        **(extra_claims or {}),
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
        "jti": str(uuid.uuid4()),
    }

    return jwt.encode(
        claims,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def verify_token(token: str) -> dict:
    """Verify a JWT token and return its claims."""
    try:
        decoded = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "iat", "exp"]},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token!",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return decoded


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token!",
        headers={"WWW-Authenticate": "Bearer"},
    )

    data = verify_token(token)
    sub = data.get("sub")

    if sub is None:
        raise credentials_exception

    try:
        user_id = int(sub)
    except ValueError:
        raise credentials_exception from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise credentials_exception

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


if __name__ == "__main__":
    password = "123456"
    hashed_password = hash_password(password)
    print(verify_password(password, hashed_password))

    token = generate_access_token("1")
    print(verify_token(token))
