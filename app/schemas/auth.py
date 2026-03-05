"""
Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Request body for POST /auth/register."""

    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=72, description="Minimum 8 characters, maximum 72")


class UserLogin(BaseModel):
    """Request body for POST /auth/login."""

    email: EmailStr
    password: str = Field(max_length=72)


class TokenResponse(BaseModel):
    """Response for successful login or register."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds


class RefreshRequest(BaseModel):
    """Request body for POST /auth/refresh."""

    refresh_token: str


class UserPublic(BaseModel):
    """Safe user representation (no password hash)."""

    id: str
    email: str
    name: str
    is_premium: bool

    class Config:
        from_attributes = True
