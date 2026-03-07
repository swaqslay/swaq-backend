"""
SQLAlchemy ORM models for Meal and MealFoodItem tables.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Meal(Base):
    """A logged meal associated with a user."""

    __tablename__ = "meals"
    __table_args__ = (
        # Fast dashboard query: "all meals for user X on date Y"
        Index("idx_meals_user_date", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    meal_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # breakfast/lunch/dinner/snack
    image_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

    # Aggregated totals (denormalized for fast dashboard queries)
    total_calories: Mapped[float] = mapped_column(Float, default=0)
    total_protein_g: Mapped[float] = mapped_column(Float, default=0)
    total_carbs_g: Mapped[float] = mapped_column(Float, default=0)
    total_fat_g: Mapped[float] = mapped_column(Float, default=0)
    total_fiber_g: Mapped[float] = mapped_column(Float, default=0)

    # AI metadata
    ai_provider: Mapped[str | None] = mapped_column(String(20))  # gemini, openrouter
    ai_model: Mapped[str | None] = mapped_column(String(100))
    ai_confidence_avg: Mapped[float] = mapped_column(Float, default=0)

    is_manually_edited: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="meals")
    food_items: Mapped[list["MealFoodItem"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan"
    )


class MealFoodItem(Base):
    """An individual food item within a meal."""

    __tablename__ = "meal_food_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    meal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meals.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    estimated_portion: Mapped[str] = mapped_column(String(100), default="1 serving")
    estimated_weight_g: Mapped[float] = mapped_column(Float, nullable=False)

    # Macros
    calories: Mapped[float] = mapped_column(Float, default=0)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    fiber_g: Mapped[float] = mapped_column(Float, default=0)

    # Micronutrients stored as JSON for flexibility
    # Structure: {"vitamin_c": {"amount": 15.2, "unit": "mg", "dv_percent": 16.9}, ...}
    vitamins: Mapped[dict] = mapped_column(JSON, default=dict)
    minerals: Mapped[dict] = mapped_column(JSON, default=dict)

    # USDA reference (if matched)
    usda_fdc_id: Mapped[int | None] = mapped_column()

    # Relationship
    meal: Mapped["Meal"] = relationship(back_populates="food_items")
