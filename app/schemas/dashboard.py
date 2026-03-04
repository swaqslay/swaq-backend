"""
Pydantic schemas for dashboard endpoints.
"""

from pydantic import BaseModel, Field

from app.schemas.nutrition import NutrientInfo


class DailyTargets(BaseModel):
    """User's daily nutrition targets from their profile."""

    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int


class DailyConsumed(BaseModel):
    """Today's consumed nutrition totals."""

    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0


class DailySummaryResponse(BaseModel):
    """Response for GET /dashboard/today."""

    date: str
    meals_logged: int
    consumed: DailyConsumed
    targets: DailyTargets
    calorie_delta: float  # negative = under, positive = over
    percent_complete: float  # calories_consumed / calorie_target * 100
    low_nutrients: list[str] = Field(
        default_factory=list,
        description="Nutrients below 50% of daily value today",
    )
    recommendations: list[str] = Field(default_factory=list)


class DayNutrientData(BaseModel):
    """Per-day micronutrient data for heatmap."""

    date: str
    nutrients: list[NutrientInfo]


class WeeklyReportResponse(BaseModel):
    """Response for GET /dashboard/weekly."""

    week_start: str
    week_end: str
    avg_daily_calories: float
    avg_daily_protein_g: float
    avg_daily_carbs_g: float
    avg_daily_fat_g: float
    total_meals_logged: int
    days_on_target: int  # Days within 10% of calorie target
    calorie_target: int
    consistently_low_nutrients: list[str]
    top_recommendation: str


class NutrientHeatmapResponse(BaseModel):
    """Response for GET /dashboard/nutrients."""

    days: list[DayNutrientData]
    nutrient_names: list[str]
