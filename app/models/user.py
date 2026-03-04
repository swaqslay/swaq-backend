"""
SQLAlchemy ORM models for User and UserProfile tables.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.meal import Meal


class User(Base):
    """Registered user account."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(back_populates="user", uselist=False)
    meals: Mapped[list["Meal"]] = relationship(back_populates="user", order_by="Meal.created_at.desc()")


class UserProfile(Base):
    """BMI, health goals, and computed daily nutrition targets for a user."""

    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    # Physical attributes
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)  # male, female, other
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    activity_level: Mapped[str] = mapped_column(String(20), default="moderate")
    health_goal: Mapped[str] = mapped_column(String(20), default="maintain")
    dietary_restrictions: Mapped[list] = mapped_column(JSON, default=list)

    # Computed targets (recalculated on profile update)
    bmi: Mapped[float] = mapped_column(Float, nullable=False)
    daily_calorie_target: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_protein_target_g: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_carb_target_g: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_fat_target_g: Mapped[int] = mapped_column(Integer, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    user: Mapped["User"] = relationship(back_populates="profile")
