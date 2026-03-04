"""
Authentication endpoints.
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
"""

import uuid
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import auth_email_exists, auth_invalid_credentials
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.auth import RefreshRequest, TokenResponse, UserLogin, UserPublic, UserRegister
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=APIResponse[TokenResponse], status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)) -> APIResponse[TokenResponse]:
    """
    Create a new user account.

    - Hashes password with bcrypt (12 rounds).
    - Returns access + refresh tokens on success.
    - Returns 400 if email is already registered.
    """
    # Check for existing email
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    if result.scalar_one_or_none():
        raise auth_email_exists()

    user = User(
        id=uuid.uuid4(),
        email=data.email.lower(),
        name=data.name.strip(),
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()

    logger.info(f"New user registered: {user.email}")

    return APIResponse.ok(
        TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )
    )


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)) -> APIResponse[TokenResponse]:
    """
    Authenticate with email + password.

    Returns access + refresh tokens on success.
    Returns 401 for any auth failure (deliberately vague to prevent enumeration).
    """
    result = await db.execute(select(User).where(User.email == data.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise auth_invalid_credentials()

    if not user.is_active:
        raise auth_invalid_credentials()

    return APIResponse.ok(
        TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )
    )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(data: RefreshRequest) -> APIResponse[TokenResponse]:
    """
    Exchange a valid refresh token for a new access token.

    Refresh tokens are valid for 30 days.
    Access tokens are valid for 15 minutes.
    """
    user_id = verify_token(data.refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    return APIResponse.ok(
        TokenResponse(
            access_token=create_access_token(user_id),
            refresh_token=create_refresh_token(user_id),  # Rotate refresh token
        )
    )
