"""
Meal service: all meal CRUD operations and DB persistence logic.
"""

import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import meal_not_found
from app.models.meal import Meal, MealFoodItem
from app.schemas.meal import MealDetailResponse, MealHistoryResponse, MealItemUpdate, MealSummary
from app.schemas.nutrition import FoodItemResponse, NutrientInfo

logger = logging.getLogger(__name__)


async def count_today_scans(user_id: uuid.UUID, db: AsyncSession) -> int:
    """Count how many meals the user has scanned today (UTC)."""
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    result = await db.execute(
        select(func.count(Meal.id)).where(
            and_(Meal.user_id == user_id, Meal.created_at >= start, Meal.created_at < end)
        )
    )
    return result.scalar_one()


async def create_meal(
    user_id: uuid.UUID,
    meal_type: str,
    food_items_data: list[dict],
    ai_provider: str,
    ai_model: str,
    image_url: str | None,
    notes: str | None,
    db: AsyncSession,
) -> Meal:
    """
    Persist a new meal and all its food items to the database.

    Args:
        food_items_data: List of dicts from the AI + nutrition service.
        All other args map directly to the Meal model.

    Returns:
        The newly created Meal ORM object (with food_items loaded).
    """
    # Calculate confidence average
    confidences = [item.get("confidence", 0.8) for item in food_items_data]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    meal = Meal(
        id=uuid.uuid4(),
        user_id=user_id,
        meal_type=meal_type,
        image_url=image_url,
        notes=notes,
        ai_provider=ai_provider,
        ai_model=ai_model,
        ai_confidence_avg=round(avg_confidence, 3),
    )
    db.add(meal)
    await db.flush()  # Get meal.id before adding food items

    total_cal = total_protein = total_carbs = total_fat = total_fiber = 0.0

    for item_data in food_items_data:
        food_item = MealFoodItem(
            id=uuid.uuid4(),
            meal_id=meal.id,
            name=item_data["name"],
            confidence=item_data.get("confidence", 0.8),
            estimated_portion=item_data.get("estimated_portion", "1 serving"),
            estimated_weight_g=item_data.get("estimated_weight_g", 100),
            calories=item_data.get("calories", 0),
            protein_g=item_data.get("protein_g", 0),
            carbs_g=item_data.get("carbs_g", 0),
            fat_g=item_data.get("fat_g", 0),
            fiber_g=item_data.get("fiber_g", 0),
            vitamins=item_data.get("vitamins", {}),
            minerals=item_data.get("minerals", {}),
            usda_fdc_id=item_data.get("usda_fdc_id"),
        )
        db.add(food_item)

        total_cal += food_item.calories
        total_protein += food_item.protein_g
        total_carbs += food_item.carbs_g
        total_fat += food_item.fat_g
        total_fiber += food_item.fiber_g

    # Update denormalized totals on the meal
    meal.total_calories = round(total_cal, 1)
    meal.total_protein_g = round(total_protein, 1)
    meal.total_carbs_g = round(total_carbs, 1)
    meal.total_fat_g = round(total_fat, 1)
    meal.total_fiber_g = round(total_fiber, 1)

    await db.flush()
    logger.info(f"Created meal {meal.id} for user {user_id} ({len(food_items_data)} items)")
    return meal


async def get_meal(meal_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Meal:
    """
    Fetch a single meal with all food items.

    Raises:
        NotFoundError: If meal doesn't exist or belongs to another user.
    """
    result = await db.execute(
        select(Meal)
        .options(selectinload(Meal.food_items))
        .where(and_(Meal.id == meal_id, Meal.user_id == user_id))
    )
    meal = result.scalar_one_or_none()
    if not meal:
        raise meal_not_found()
    return meal


async def get_meal_history(
    user_id: uuid.UUID,
    target_date: date,
    db: AsyncSession,
) -> MealHistoryResponse:
    """
    Get all meals for a user on a specific date.

    Args:
        target_date: The date to query (UTC).
    """
    start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    result = await db.execute(
        select(Meal)
        .options(selectinload(Meal.food_items))
        .where(
            and_(
                Meal.user_id == user_id,
                Meal.created_at >= start,
                Meal.created_at < end,
            )
        )
        .order_by(Meal.created_at.asc())
    )
    meals = result.scalars().all()

    summaries = [
        MealSummary(
            id=str(m.id),
            meal_type=m.meal_type,
            image_url=m.image_url,
            total_calories=m.total_calories,
            total_protein_g=m.total_protein_g,
            total_carbs_g=m.total_carbs_g,
            total_fat_g=m.total_fat_g,
            food_items_count=len(m.food_items),
            created_at=m.created_at,
        )
        for m in meals
    ]

    # Daily totals
    daily_totals = {
        "calories": round(sum(m.total_calories for m in meals), 1),
        "protein_g": round(sum(m.total_protein_g for m in meals), 1),
        "carbs_g": round(sum(m.total_carbs_g for m in meals), 1),
        "fat_g": round(sum(m.total_fat_g for m in meals), 1),
    }

    return MealHistoryResponse(
        date=target_date.isoformat(),
        meals=summaries,
        daily_totals=daily_totals,
    )


async def update_meal_item(
    meal_id: uuid.UUID,
    item_id: uuid.UUID,
    user_id: uuid.UUID,
    data: MealItemUpdate,
    db: AsyncSession,
) -> Meal:
    """
    Manually correct a food item. Recalculates meal totals.

    Raises:
        NotFoundError: If meal or item not found.
    """
    meal = await get_meal(meal_id, user_id, db)

    item = next((i for i in meal.food_items if i.id == item_id), None)
    if not item:
        raise meal_not_found()

    # Apply updates
    update_data = data.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    # Recalculate meal totals
    meal.total_calories = round(sum(i.calories for i in meal.food_items), 1)
    meal.total_protein_g = round(sum(i.protein_g for i in meal.food_items), 1)
    meal.total_carbs_g = round(sum(i.carbs_g for i in meal.food_items), 1)
    meal.total_fat_g = round(sum(i.fat_g for i in meal.food_items), 1)
    meal.total_fiber_g = round(sum(i.fiber_g for i in meal.food_items), 1)
    meal.is_manually_edited = True

    await db.flush()
    return meal


async def delete_meal(meal_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    """
    Delete a meal and all its food items (cascade).

    Raises:
        NotFoundError: If meal not found or belongs to another user.
    """
    meal = await get_meal(meal_id, user_id, db)
    await db.delete(meal)
    await db.flush()
    logger.info(f"Deleted meal {meal_id} for user {user_id}")


def build_meal_detail_response(meal: Meal) -> MealDetailResponse:
    """Convert a Meal ORM object to the detail response schema."""
    food_items = []
    all_vitamins: dict = {}
    all_minerals: dict = {}

    for item in meal.food_items:
        vitamins = [
            NutrientInfo(
                name=k, amount=v["amount"], unit=v["unit"], daily_value_percent=v.get("dv_percent")
            )
            for k, v in (item.vitamins or {}).items()
        ]
        minerals = [
            NutrientInfo(
                name=k, amount=v["amount"], unit=v["unit"], daily_value_percent=v.get("dv_percent")
            )
            for k, v in (item.minerals or {}).items()
        ]

        food_items.append(
            FoodItemResponse(
                id=str(item.id),
                name=item.name,
                confidence=item.confidence,
                estimated_portion=item.estimated_portion,
                estimated_weight_g=item.estimated_weight_g,
                calories=item.calories,
                protein_g=item.protein_g,
                carbs_g=item.carbs_g,
                fat_g=item.fat_g,
                fiber_g=item.fiber_g,
                vitamins=vitamins,
                minerals=minerals,
            )
        )

        # Aggregate micronutrients
        for v in vitamins:
            if v.name in all_vitamins:
                all_vitamins[v.name]["amount"] += v.amount
            else:
                all_vitamins[v.name] = {
                    "amount": v.amount,
                    "unit": v.unit,
                    "dvp": v.daily_value_percent or 0,
                }
        for m in minerals:
            if m.name in all_minerals:
                all_minerals[m.name]["amount"] += m.amount
            else:
                all_minerals[m.name] = {
                    "amount": m.amount,
                    "unit": m.unit,
                    "dvp": m.daily_value_percent or 0,
                }

    vitamins_summary = [
        NutrientInfo(
            name=n,
            amount=round(d["amount"], 1),
            unit=d["unit"],
            daily_value_percent=round(d["dvp"], 1),
        )
        for n, d in all_vitamins.items()
    ]
    minerals_summary = [
        NutrientInfo(
            name=n,
            amount=round(d["amount"], 1),
            unit=d["unit"],
            daily_value_percent=round(d["dvp"], 1),
        )
        for n, d in all_minerals.items()
    ]

    return MealDetailResponse(
        id=str(meal.id),
        meal_type=meal.meal_type,
        image_url=meal.image_url,
        notes=meal.notes,
        food_items=food_items,
        total_calories=meal.total_calories,
        total_protein_g=meal.total_protein_g,
        total_carbs_g=meal.total_carbs_g,
        total_fat_g=meal.total_fat_g,
        total_fiber_g=meal.total_fiber_g,
        vitamins_summary=vitamins_summary,
        minerals_summary=minerals_summary,
        ai_provider=meal.ai_provider,
        ai_model=meal.ai_model,
        is_manually_edited=meal.is_manually_edited,
        created_at=meal.created_at,
    )
