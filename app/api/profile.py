"""
User Profile API Endpoints

POST /api/profile          - Create/update user profile
GET  /api/profile          - Get user profile with BMI & targets
GET  /api/profile/targets  - Get daily nutrition targets only
"""

from fastapi import APIRouter
from app.models.user import UserProfile, UserProfileResponse
from app.services.bmi_calculator import calculate_daily_targets

router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.post("/", response_model=UserProfileResponse)
async def create_or_update_profile(profile: UserProfile):
    """
    Create or update the user's profile.
    Automatically calculates BMI, BMR, and daily nutrition targets.

    Required fields: age, gender, height_cm, weight_kg
    Optional: activity_level, health_goal, dietary_restrictions
    """
    targets = calculate_daily_targets(profile)

    return UserProfileResponse(
        **profile.model_dump(),
        bmi=targets["bmi"],
        bmi_category=targets["bmi_category"],
        daily_calorie_target=targets["daily_calorie_target"],
        daily_protein_target_g=targets["daily_protein_target_g"],
        daily_carb_target_g=targets["daily_carb_target_g"],
        daily_fat_target_g=targets["daily_fat_target_g"],
    )


@router.get("/targets")
async def get_daily_targets():
    """
    Get daily nutrition targets for the current user.
    Placeholder - will read from DB once auth is implemented.
    """
    return {
        "message": "Connect to DB to fetch saved profile",
        "example_targets": {
            "daily_calorie_target": 2200,
            "daily_protein_target_g": 138,
            "daily_carb_target_g": 275,
            "daily_fat_target_g": 61,
        }
    }
