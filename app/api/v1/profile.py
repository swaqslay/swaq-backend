"""
User profile endpoints.
POST  /api/v1/profile        - Create or replace profile
GET   /api/v1/profile        - Get current profile with targets
PATCH /api/v1/profile        - Partial update, recalculates targets
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.user import ProfileCreate, ProfileResponse, ProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.post("/", response_model=APIResponse[ProfileResponse], status_code=201)
async def create_profile(
    data: ProfileCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProfileResponse]:
    """
    Create or replace the user's profile.
    Automatically calculates BMI, BMR, TDEE, and daily macro targets.
    """
    profile = await profile_service.create_or_update_profile(current_user.id, data, db)
    return APIResponse.ok(profile)


@router.get("/", response_model=APIResponse[ProfileResponse])
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProfileResponse]:
    """Get the current user's profile with all computed nutrition targets."""
    from app.services.bmi_calculator import calculate_daily_targets

    profile_orm = await profile_service.get_profile(current_user.id, db)
    targets = calculate_daily_targets(
        age=profile_orm.age,
        gender=profile_orm.gender,
        height_cm=profile_orm.height_cm,
        weight_kg=profile_orm.weight_kg,
        activity_level=profile_orm.activity_level,
        health_goal=profile_orm.health_goal,
    )
    response = ProfileResponse(
        age=profile_orm.age,
        gender=profile_orm.gender,
        height_cm=profile_orm.height_cm,
        weight_kg=profile_orm.weight_kg,
        activity_level=profile_orm.activity_level,
        health_goal=profile_orm.health_goal,
        dietary_restrictions=profile_orm.dietary_restrictions or [],
        bmi=profile_orm.bmi,
        bmi_category=targets["bmi_category"],
        daily_calorie_target=profile_orm.daily_calorie_target,
        daily_protein_target_g=profile_orm.daily_protein_target_g,
        daily_carb_target_g=profile_orm.daily_carb_target_g,
        daily_fat_target_g=profile_orm.daily_fat_target_g,
    )
    return APIResponse.ok(response)


@router.patch("/", response_model=APIResponse[ProfileResponse])
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[ProfileResponse]:
    """
    Partially update the user's profile.
    Only provided fields are changed. Targets are recalculated automatically.
    """
    profile = await profile_service.patch_profile(current_user.id, data, db)
    return APIResponse.ok(profile)
