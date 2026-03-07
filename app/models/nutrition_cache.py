"""
SQLAlchemy ORM model for the nutrition_cache table.
Caches USDA and AI-estimated nutrition data to reduce API calls.
"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NutritionCache(Base):
    """
    Persistent cache for nutrition lookup results.
    Redis is the hot layer (7-day TTL); this table is the permanent store.
    """

    __tablename__ = "nutrition_cache"
    __table_args__ = (Index("idx_nutrition_cache_name", "food_name_normalized"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    food_name_normalized: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    usda_fdc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nutrition_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(20))  # usda, ifct, ai_estimated
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
