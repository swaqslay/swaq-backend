"""
Shared FastAPI dependencies.
Used via Depends() in route handlers.
"""

import logging
import uuid

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import auth_token_invalid
from app.core.security import ACCESS_TOKEN_TYPE, verify_token
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract and validate the Bearer token from the Authorization header.
    Fetches and returns the corresponding User from the database.

    Raises:
        AuthenticationError: If header is missing, token is invalid, or user not found.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise auth_token_invalid()

    token = authorization.removeprefix("Bearer ").strip()
    user_id_str = verify_token(token, expected_type=ACCESS_TOKEN_TYPE)

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise auth_token_invalid()

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise auth_token_invalid()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Like get_current_user, but also verifies the account is active (not banned).

    Raises:
        AuthenticationError: If the account is deactivated.
    """
    if not current_user.is_active:
        from app.core.exceptions import AuthenticationError

        raise AuthenticationError("Account is deactivated.", "ACCOUNT_DEACTIVATED")
    return current_user
