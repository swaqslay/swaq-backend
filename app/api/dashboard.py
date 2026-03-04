"""
Dashboard API Endpoints

GET /api/dashboard/today   - Today's nutrition summary with recommendations
GET /api/dashboard/weekly  - Weekly nutrition report
"""

from fastapi import APIRouter
from app.services.bmi_calculator import generate_recommendations

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/today")
async def get_today_summary():
    """
    Get today's nutrition summary: consumed vs targets.
    Returns personalized recommendations.

    Note: This is a demo response. In production, this aggregates
    from the meals database for the authenticated user.
    """
    # Demo data - in production, query from DB
    calories_consumed = 1450
    protein_consumed = 65
    calorie_target = 2200
    protein_target = 138
    low_nutrients = ["Vitamin D", "Calcium", "Iron"]

    recommendations = generate_recommendations(
        calories_consumed=calories_consumed,
        protein_consumed=protein_consumed,
        calorie_target=calorie_target,
        protein_target=protein_target,
        low_nutrients=low_nutrients,
    )

    return {
        "date": "today",
        "meals_logged": 2,
        "consumed": {
            "calories": calories_consumed,
            "protein_g": protein_consumed,
            "carbs_g": 180,
            "fat_g": 45,
        },
        "targets": {
            "calories": calorie_target,
            "protein_g": protein_target,
            "carbs_g": 275,
            "fat_g": 61,
        },
        "calorie_delta": calories_consumed - calorie_target,
        "low_nutrients": low_nutrients,
        "recommendations": recommendations,
    }


@router.get("/weekly")
async def get_weekly_report():
    """Weekly nutrition report. Placeholder for DB integration."""
    return {
        "message": "Weekly report - connect to DB for real data",
        "week": "current",
    }
