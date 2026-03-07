"""
Inline meal scan processor.

Processes a food photo synchronously within the HTTP request:
  1. AI food recognition + nutrition estimation (combined single call)
  2. USDA nutrition enrichment (parallel lookups)
  3. Save meal to database
  4. Generate recommendations
  5. Return MealScanResponse
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import meal_scan_failed
from app.models.user import UserProfile
from app.schemas.meal import MealScanResponse
from app.schemas.nutrition import FoodItemResponse, NutrientInfo
from app.services import meal_service
from app.services.ai_food_recognizer import AIFoodRecognizer
from app.services.nutrition_lookup import NutritionLookup
from app.services.recommendation_engine import generate_recommendations

logger = logging.getLogger(__name__)


async def process_scan_inline(
    image_bytes: bytes,
    content_type: str,
    user_id: uuid.UUID,
    meal_type: str,
    notes: str | None,
    image_url: str | None,
    db: AsyncSession,
    redis: object | None,
) -> MealScanResponse:
    """
    Process a food photo scan inline within the HTTP request.

    Args:
        image_bytes: Raw image bytes (already validated for format/size).
        content_type: MIME type of the image.
        user_id: Authenticated user's UUID.
        meal_type: One of breakfast, lunch, dinner, snack.
        notes: Optional user notes for the meal.
        image_url: URL of uploaded image (or None if storage not configured).
        db: Database session from request dependency injection.
        redis: Redis client (optional — caching skipped if None).

    Returns:
        MealScanResponse with full nutrition breakdown.

    Raises:
        ValidationError (MEAL_SCAN_FAILED): If AI returns no food items.
        AIProviderError / ServiceUnavailableError: If all AI providers fail.
    """
    recognizer = None
    nutrition_service = None
    try:
        # Step 1: AI recognition + nutrition (combined single call)
        recognizer = AIFoodRecognizer()
        recognition = await recognizer.analyze_food_image_with_nutrition(image_bytes, content_type)

        raw_food_items = recognition.get("food_items", [])
        if not raw_food_items:
            raise meal_scan_failed()

        ai_provider = recognition.get("_ai_provider", "unknown")
        ai_model = recognition.get("_ai_model", "unknown")

        # Combined result already has nutrition embedded in food_items
        nutrition_items = raw_food_items

        nutrition_service = NutritionLookup()

        # Step 2: Parallel USDA lookups
        # WARNING: db session is shared across concurrent lookups.
        # Safe for Redis-cached hits; DB writes in _store_in_cache are
        # wrapped in try/except. See plan-v2.md risk area #3.
        async def _lookup_one(item: dict) -> tuple[dict, dict]:
            """Lookup nutrition for a single item, return (item, nutrition)."""
            weight_g = item.get("estimated_weight_g", 100)
            nutrition = await nutrition_service.get_nutrition_with_cache(
                food_name=item["name"],
                weight_g=weight_g,
                ai_estimate=item,
                redis=redis,
                db=db,
            )
            return item, nutrition

        results = await asyncio.gather(
            *[_lookup_one(item) for item in nutrition_items],
            return_exceptions=True,
        )

        # Step 3: Build enriched items list
        enriched_items: list[dict] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Nutrition lookup failed for an item: %s", result)
                continue
            item, nutrition = result
            enriched_items.append(
                {
                    "name": item["name"],
                    "confidence": item.get("confidence", 0.8),
                    "estimated_portion": item.get("estimated_portion", "1 serving"),
                    "estimated_weight_g": item.get("estimated_weight_g", 100),
                    "calories": nutrition.get("calories", item.get("calories", 0)),
                    "protein_g": nutrition.get("protein_g", item.get("protein_g", 0)),
                    "carbs_g": nutrition.get("carbs_g", item.get("carbs_g", 0)),
                    "fat_g": nutrition.get("fat_g", item.get("fat_g", 0)),
                    "fiber_g": nutrition.get("fiber_g", item.get("fiber_g", 0)),
                    "vitamins": nutrition.get("vitamins", {}),
                    "minerals": nutrition.get("minerals", {}),
                }
            )

        # Step 4: Save to database
        meal = await meal_service.create_meal(
            user_id=user_id,
            meal_type=meal_type,
            food_items_data=enriched_items,
            ai_provider=ai_provider,
            ai_model=ai_model,
            image_url=image_url,
            notes=notes,
            db=db,
        )
        await db.commit()

        # Step 5: Build response objects
        food_item_responses = []
        all_vitamins: dict = {}
        all_minerals: dict = {}

        for item_data in enriched_items:
            vitamins = [
                NutrientInfo(
                    name=k,
                    amount=v["amount"],
                    unit=v["unit"],
                    daily_value_percent=v.get("dv_percent"),
                )
                for k, v in item_data.get("vitamins", {}).items()
            ]
            minerals = [
                NutrientInfo(
                    name=k,
                    amount=v["amount"],
                    unit=v["unit"],
                    daily_value_percent=v.get("dv_percent"),
                )
                for k, v in item_data.get("minerals", {}).items()
            ]

            food_item_responses.append(
                FoodItemResponse(
                    id=str(uuid.uuid4()),
                    name=item_data["name"],
                    confidence=item_data["confidence"],
                    estimated_portion=item_data["estimated_portion"],
                    estimated_weight_g=item_data["estimated_weight_g"],
                    calories=item_data["calories"],
                    protein_g=item_data["protein_g"],
                    carbs_g=item_data["carbs_g"],
                    fat_g=item_data["fat_g"],
                    fiber_g=item_data["fiber_g"],
                    vitamins=vitamins,
                    minerals=minerals,
                )
            )

            for v in vitamins:
                if v.name not in all_vitamins:
                    all_vitamins[v.name] = {
                        "amount": v.amount,
                        "unit": v.unit,
                        "dvp": v.daily_value_percent or 0,
                    }
                else:
                    all_vitamins[v.name]["amount"] += v.amount

            for m in minerals:
                if m.name not in all_minerals:
                    all_minerals[m.name] = {
                        "amount": m.amount,
                        "unit": m.unit,
                        "dvp": m.daily_value_percent or 0,
                    }
                else:
                    all_minerals[m.name]["amount"] += m.amount

        # Detect low nutrients (below 50% DV)
        low_nutrients = [
            name for name, d in {**all_vitamins, **all_minerals}.items() if d["dvp"] < 50
        ]

        # Step 6: Generate recommendations if user has a profile
        recommendations: list[str] = []
        try:
            result_set = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
            profile = result_set.scalar_one_or_none()
            if profile:
                recommendations = generate_recommendations(
                    calories_consumed=meal.total_calories,
                    protein_consumed=meal.total_protein_g,
                    calorie_target=profile.daily_calorie_target,
                    protein_target=profile.daily_protein_target_g,
                    low_nutrients=low_nutrients,
                )
        except Exception as exc:
            logger.warning("Failed to generate recommendations: %s", exc)

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

        # Step 7: Return MealScanResponse
        return MealScanResponse(
            meal_id=str(meal.id),
            meal_type=meal_type,
            image_url=image_url,
            food_items=food_item_responses,
            total_calories=meal.total_calories,
            total_protein_g=meal.total_protein_g,
            total_carbs_g=meal.total_carbs_g,
            total_fat_g=meal.total_fat_g,
            total_fiber_g=meal.total_fiber_g,
            vitamins_summary=vitamins_summary,
            minerals_summary=minerals_summary,
            ai_provider=ai_provider,
            ai_model=ai_model,
            analyzed_at=datetime.now(timezone.utc),
            recommendations=recommendations,
        )

    finally:
        # Close HTTP clients but NOT db — the route handler owns the session lifecycle.
        for obj in (recognizer, nutrition_service):
            if obj is not None and hasattr(obj, "close"):
                try:
                    await obj.close()
                except Exception:
                    pass
