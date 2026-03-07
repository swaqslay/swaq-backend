"""
Profile service: create/update user profiles with BMI/BMR/TDEE calculations.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import profile_not_found
from app.models.user import UserProfile
from app.schemas.user import ProfileCreate, ProfileResponse, ProfileUpdate
from app.services.bmi_calculator import calculate_daily_targets

logger = logging.getLogger(__name__)


async def get_profile(user_id: uuid.UUID, db: AsyncSession) -> UserProfile:
    """
    Retrieve a user's profile from the database.

    Raises:
        NotFoundError: If the user has no profile yet.
    """
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise profile_not_found()
    return profile


async def create_or_update_profile(
    user_id: uuid.UUID,
    data: ProfileCreate,
    db: AsyncSession,
) -> ProfileResponse:
    """
    Create or update the user's profile.
    Automatically recalculates BMI, BMR, TDEE, and macro targets.

    Returns:
        ProfileResponse with computed targets included.
    """
    # Calculate all targets from the input data
    targets = calculate_daily_targets(
        age=data.age,
        gender=data.gender,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        activity_level=data.activity_level,
        health_goal=data.health_goal,
    )

    # Check if profile already exists
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()

    if profile:
        # Update existing profile
        profile.age = data.age
        profile.gender = data.gender
        profile.height_cm = data.height_cm
        profile.weight_kg = data.weight_kg
        profile.activity_level = data.activity_level
        profile.health_goal = data.health_goal
        profile.dietary_restrictions = data.dietary_restrictions
        profile.bmi = targets["bmi"]
        profile.daily_calorie_target = targets["daily_calorie_target"]
        profile.daily_protein_target_g = targets["daily_protein_target_g"]
        profile.daily_carb_target_g = targets["daily_carb_target_g"]
        profile.daily_fat_target_g = targets["daily_fat_target_g"]
        logger.info(f"Updated profile for user {user_id}")
    else:
        # Create new profile
        profile = UserProfile(
            id=uuid.uuid4(),
            user_id=user_id,
            age=data.age,
            gender=data.gender,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            activity_level=data.activity_level,
            health_goal=data.health_goal,
            dietary_restrictions=data.dietary_restrictions,
            bmi=targets["bmi"],
            daily_calorie_target=targets["daily_calorie_target"],
            daily_protein_target_g=targets["daily_protein_target_g"],
            daily_carb_target_g=targets["daily_carb_target_g"],
            daily_fat_target_g=targets["daily_fat_target_g"],
        )
        db.add(profile)
        logger.info(f"Created new profile for user {user_id}")

    await db.flush()

    return ProfileResponse(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        health_goal=profile.health_goal,
        dietary_restrictions=profile.dietary_restrictions,
        bmi=profile.bmi,
        bmi_category=targets["bmi_category"],
        daily_calorie_target=profile.daily_calorie_target,
        daily_protein_target_g=profile.daily_protein_target_g,
        daily_carb_target_g=profile.daily_carb_target_g,
        daily_fat_target_g=profile.daily_fat_target_g,
    )


async def patch_profile(
    user_id: uuid.UUID,
    data: ProfileUpdate,
    db: AsyncSession,
) -> ProfileResponse:
    """
    Partially update a profile. Recalculates targets only for changed fields.

    Raises:
        NotFoundError: If no profile exists.
    """
    profile = await get_profile(user_id, db)

    # Apply only the provided fields
    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    # Recalculate targets with updated data
    targets = calculate_daily_targets(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        health_goal=profile.health_goal,
    )

    profile.bmi = targets["bmi"]
    profile.daily_calorie_target = targets["daily_calorie_target"]
    profile.daily_protein_target_g = targets["daily_protein_target_g"]
    profile.daily_carb_target_g = targets["daily_carb_target_g"]
    profile.daily_fat_target_g = targets["daily_fat_target_g"]

    await db.flush()

    return ProfileResponse(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=profile.activity_level,
        health_goal=profile.health_goal,
        dietary_restrictions=profile.dietary_restrictions or [],
        bmi=profile.bmi,
        bmi_category=targets["bmi_category"],
        daily_calorie_target=profile.daily_calorie_target,
        daily_protein_target_g=profile.daily_protein_target_g,
        daily_carb_target_g=profile.daily_carb_target_g,
        daily_fat_target_g=profile.daily_fat_target_g,
    )
