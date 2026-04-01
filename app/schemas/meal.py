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


# ── Text-based meal logging schemas ──────────────────────────────────────────


class TextMealItemInput(BaseModel):
    """A single food item in a text-based meal log."""

    name: str = Field(..., min_length=1, max_length=200)
    portion: str | None = Field(None, max_length=100)
    estimated_weight_g: float = Field(..., gt=0)


class TextMealLogRequest(BaseModel):
    """Request body for POST /meals/log (text-based logging)."""

    meal_type: str = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    items: list[TextMealItemInput] = Field(..., min_length=1)
    notes: str | None = None


# ── Quick snack shortcut schemas ─────────────────────────────────────────────


class QuickSnackLogRequest(BaseModel):
    """Request body for POST /meals/quick-log."""

    snack_id: str = Field(..., min_length=1)
    quantity: int = Field(default=1, ge=1, le=10)
    meal_type: str = Field(default="snack", pattern="^(breakfast|lunch|dinner|snack)$")


class QuickSnackInfo(BaseModel):
    """A single snack in the quick-snacks catalog."""

    id: str
    name: str
    emoji: str
    default_portion: str
    calories: float
    category: str


class QuickSnackListResponse(BaseModel):
    """Response for GET /meals/quick-snacks."""

    snacks: list[QuickSnackInfo]
