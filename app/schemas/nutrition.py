"""
Pydantic schemas for nutrition data structures.
Used by meal scan responses and dashboard.
"""

from typing import Optional

from pydantic import BaseModel, Field


class NutrientInfo(BaseModel):
    """Individual nutrient data point."""

    name: str
    amount: float
    unit: str
    daily_value_percent: Optional[float] = None


class FoodItemResponse(BaseModel):
    """A single identified food item with full nutrition breakdown."""

    id: str
    name: str
    confidence: float = Field(ge=0, le=1)
    estimated_portion: str
    estimated_weight_g: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0
    vitamins: list[NutrientInfo] = Field(default_factory=list)
    minerals: list[NutrientInfo] = Field(default_factory=list)

    class Config:
        from_attributes = True
