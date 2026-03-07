"""
Dashboard endpoints — aggregated nutrition summaries and recommendations.
GET /api/v1/dashboard/today     - Today's consumed vs targets
GET /api/v1/dashboard/weekly    - 7-day averages and trends
GET /api/v1/dashboard/nutrients - Micronutrient heatmap (7 days)
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import profile_not_found
from app.models.meal import Meal
from app.models.user import User, UserProfile
from app.schemas.common import APIResponse
from app.schemas.dashboard import (
    DailyConsumed,
    DailySummaryResponse,
    DailyTargets,
    WeeklyReportResponse,
)
from app.services.recommendation_engine import generate_recommendations
from app.utils.helpers import get_today_utc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


async def _get_profile_or_raise(user_id, db: AsyncSession) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise profile_not_found()
    return profile


@router.get("/today", response_model=APIResponse[DailySummaryResponse])
async def get_today_summary(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[DailySummaryResponse]:
    """
    Get today's nutrition: consumed vs targets, plus personalized recommendations.

    Requires the user to have created a profile first.
    """
    profile = await _get_profile_or_raise(current_user.id, db)

    # Query today's meals
    today = get_today_utc()
    start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    result = await db.execute(
        select(
            func.count(Meal.id),
            func.coalesce(func.sum(Meal.total_calories), 0),
            func.coalesce(func.sum(Meal.total_protein_g), 0),
            func.coalesce(func.sum(Meal.total_carbs_g), 0),
            func.coalesce(func.sum(Meal.total_fat_g), 0),
            func.coalesce(func.sum(Meal.total_fiber_g), 0),
        ).where(
            and_(Meal.user_id == current_user.id, Meal.created_at >= start, Meal.created_at < end)
        )
    )
    row = result.one()
    meals_count, cal, protein, carbs, fat, fiber = row

    calorie_delta = cal - profile.daily_calorie_target
    percent_complete = round(cal / max(profile.daily_calorie_target, 1) * 100, 1)

    # Determine low nutrients (simplified: placeholder for micronutrient aggregation)
    low_nutrients: list[str] = []

    recommendations = generate_recommendations(
        calories_consumed=float(cal),
        protein_consumed=float(protein),
        calorie_target=profile.daily_calorie_target,
        protein_target=profile.daily_protein_target_g,
        low_nutrients=low_nutrients,
    )

    return APIResponse.ok(
        DailySummaryResponse(
            date=today.isoformat(),
            meals_logged=meals_count,
            consumed=DailyConsumed(
                calories=round(float(cal), 1),
                protein_g=round(float(protein), 1),
                carbs_g=round(float(carbs), 1),
                fat_g=round(float(fat), 1),
                fiber_g=round(float(fiber), 1),
            ),
            targets=DailyTargets(
                calories=profile.daily_calorie_target,
                protein_g=profile.daily_protein_target_g,
                carbs_g=profile.daily_carb_target_g,
                fat_g=profile.daily_fat_target_g,
            ),
            calorie_delta=round(float(calorie_delta), 1),
            percent_complete=percent_complete,
            low_nutrients=low_nutrients,
            recommendations=recommendations,
        )
    )


@router.get("/weekly", response_model=APIResponse[WeeklyReportResponse])
async def get_weekly_report(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[WeeklyReportResponse]:
    """Get a 7-day nutrition summary with averages and trends."""
    profile = await _get_profile_or_raise(current_user.id, db)

    today = get_today_utc()
    week_start = today - timedelta(days=6)
    start_dt = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(today, datetime.max.time()).replace(tzinfo=timezone.utc)

    result = await db.execute(
        select(
            func.count(Meal.id),
            func.coalesce(func.sum(Meal.total_calories), 0),
            func.coalesce(func.sum(Meal.total_protein_g), 0),
            func.coalesce(func.sum(Meal.total_carbs_g), 0),
            func.coalesce(func.sum(Meal.total_fat_g), 0),
        ).where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= start_dt,
                Meal.created_at <= end_dt,
            )
        )
    )
    row = result.one()
    total_meals, total_cal, total_protein, total_carbs, total_fat = row

    days = 7
    avg_cal = round(float(total_cal) / days, 1)
    avg_protein = round(float(total_protein) / days, 1)
    avg_carbs = round(float(total_carbs) / days, 1)
    avg_fat = round(float(total_fat) / days, 1)

    # Count days within 10% of calorie target
    target = profile.daily_calorie_target
    lower = target * 0.9
    upper = target * 1.1

    days_result = await db.execute(
        select(
            func.date(Meal.created_at),
            func.sum(Meal.total_calories),
        )
        .where(
            and_(
                Meal.user_id == current_user.id,
                Meal.created_at >= start_dt,
                Meal.created_at <= end_dt,
            )
        )
        .group_by(func.date(Meal.created_at))
    )
    days_on_target = sum(1 for _, day_cal in days_result.all() if lower <= float(day_cal) <= upper)

    recs = generate_recommendations(
        calories_consumed=avg_cal,
        protein_consumed=avg_protein,
        calorie_target=target,
        protein_target=profile.daily_protein_target_g,
        low_nutrients=[],
    )

    return APIResponse.ok(
        WeeklyReportResponse(
            week_start=week_start.isoformat(),
            week_end=today.isoformat(),
            avg_daily_calories=avg_cal,
            avg_daily_protein_g=avg_protein,
            avg_daily_carbs_g=avg_carbs,
            avg_daily_fat_g=avg_fat,
            total_meals_logged=int(total_meals),
            days_on_target=days_on_target,
            calorie_target=target,
            consistently_low_nutrients=[],
            top_recommendation=recs[0] if recs else "Keep tracking your meals!",
        )
    )
