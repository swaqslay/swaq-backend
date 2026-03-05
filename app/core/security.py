"""
JWT token creation/verification and bcrypt password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import auth_token_expired, auth_token_invalid

settings = get_settings()

# bcrypt context — 12 rounds for security
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Token type markers
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt (12 rounds)."""
    # Defensive check: bcrypt has a 72-byte limit. We truncate here as well.
    # Note: str.encode('utf-8')[:72] would be safer if we care about byte length.
    return _pwd_context.hash(plain_password[:72])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    """
    Create a short-lived JWT access token (15 minutes).

    Args:
        user_id: The UUID of the authenticated user.

    Returns:
        Signed JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "type": ACCESS_TOKEN_TYPE,
        "exp": expire,
        "iss": "swaq-api",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    """
    Create a long-lived JWT refresh token (30 days).

    Args:
        user_id: The UUID of the authenticated user.

    Returns:
        Signed JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "type": REFRESH_TOKEN_TYPE,
        "exp": expire,
        "iss": "swaq-api",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str, expected_type: str) -> str:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT string to verify.
        expected_type: "access" or "refresh".

    Returns:
        The user_id (sub claim) extracted from the token.

    Raises:
        AuthenticationError: If token is invalid, expired, or wrong type.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_iss": False},
        )
        user_id: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("type")

        if user_id is None:
            raise auth_token_invalid()
        if token_type != expected_type:
            raise auth_token_invalid()

        return user_id

    except JWTError as exc:
        # Distinguish expired from invalid
        if "expired" in str(exc).lower():
            raise auth_token_expired()
        raise auth_token_invalid()
