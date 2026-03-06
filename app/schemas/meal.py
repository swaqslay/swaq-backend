"""
Pydantic schemas for meal-related endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.nutrition import FoodItemResponse, NutrientInfo


class MealScanResponse(BaseModel):
    """Response for POST /meals/scan."""

    meal_id: str
    meal_type: str
    image_url: str | None = None
    food_items: list[FoodItemResponse]
    # Aggregated totals
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    # Aggregated micronutrients
    vitamins_summary: list[NutrientInfo] = Field(default_factory=list)
    minerals_summary: list[NutrientInfo] = Field(default_factory=list)
    # AI metadata
    ai_provider: str
    ai_model: str
    analyzed_at: datetime
    # Personalized recommendations (if profile exists)
    recommendations: list[str] = Field(default_factory=list)


class MealSummary(BaseModel):
    """Brief meal info for history listing."""

    id: str
    meal_type: str
    image_url: str | None = None
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    food_items_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class MealDetailResponse(BaseModel):
    """Full meal detail for GET /meals/{id}."""

    id: str
    meal_type: str
    image_url: str | None = None
    notes: str | None = None
    food_items: list[FoodItemResponse]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    total_fiber_g: float
    vitamins_summary: list[NutrientInfo] = Field(default_factory=list)
    minerals_summary: list[NutrientInfo] = Field(default_factory=list)
    ai_provider: str | None = None
    ai_model: str | None = None
    is_manually_edited: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MealHistoryResponse(BaseModel):
    """Response for GET /meals/history."""

    date: str
    meals: list[MealSummary]
    daily_totals: dict


class ScanSubmitResponse(BaseModel):
    """Response for POST /meals/scan — immediate acknowledgement."""

    scan_id: str
    status: str  # always "pending"
    poll_url: str


class ScanStatusResponse(BaseModel):
    """Response for GET /meals/scan/{scan_id}/status — polling result."""

    scan_id: str
    status: str  # pending | processing | completed | failed
    meal_id: str | None = None
    result: MealScanResponse | None = None
    error: dict | None = None


class MealItemUpdate(BaseModel):
    """Request body for PATCH /meals/{id}/items/{item_id}."""

    name: str | None = None
    estimated_portion: str | None = None
    estimated_weight_g: float | None = Field(None, gt=0)
    calories: float | None = Field(None, ge=0)
    protein_g: float | None = Field(None, ge=0)
    carbs_g: float | None = Field(None, ge=0)
    fat_g: float | None = Field(None, ge=0)
    fiber_g: float | None = Field(None, ge=0)
