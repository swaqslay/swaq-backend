"""
Pydantic schemas for user profile endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    """Request body for POST /profile."""

    age: int = Field(ge=13, le=120)
    gender: str = Field(pattern="^(male|female|other)$")
    height_cm: float = Field(ge=100, le=250, description="Height in centimeters")
    weight_kg: float = Field(ge=30, le=300, description="Weight in kilograms")
    activity_level: str = Field(
        default="moderate",
        pattern="^(sedentary|light|moderate|active|very_active)$",
    )
    health_goal: str = Field(
        default="maintain",
        pattern="^(lose_weight|maintain|gain_weight|build_muscle)$",
    )
    dietary_restrictions: list[str] = Field(
        default_factory=list,
        description="e.g. vegetarian, vegan, gluten-free",
    )


class ProfileUpdate(BaseModel):
    """Request body for PATCH /profile — all fields optional."""

    age: Optional[int] = Field(None, ge=13, le=120)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    height_cm: Optional[float] = Field(None, ge=100, le=250)
    weight_kg: Optional[float] = Field(None, ge=30, le=300)
    activity_level: Optional[str] = Field(None, pattern="^(sedentary|light|moderate|active|very_active)$")
    health_goal: Optional[str] = Field(None, pattern="^(lose_weight|maintain|gain_weight|build_muscle)$")
    dietary_restrictions: Optional[list[str]] = None


class ProfileResponse(BaseModel):
    """Response for GET/POST/PATCH /profile."""

    age: int
    gender: str
    height_cm: float
    weight_kg: float
    activity_level: str
    health_goal: str
    dietary_restrictions: list[str]
    bmi: float
    bmi_category: str
    daily_calorie_target: int
    daily_protein_target_g: int
    daily_carb_target_g: int
    daily_fat_target_g: int

    class Config:
        from_attributes = True
