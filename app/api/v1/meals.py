"""
Meal endpoints — THIN controllers, all logic in meal_service.
POST   /api/v1/meals/scan             - Upload photo → AI analysis → save
GET    /api/v1/meals/history          - Meal history for a date
GET    /api/v1/meals/{meal_id}        - Single meal detail
PATCH  /api/v1/meals/{meal_id}/items/{item_id} - Manual correction
DELETE /api/v1/meals/{meal_id}        - Delete meal
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.core.exceptions import (
    meal_image_invalid,
    meal_image_too_large,
    meal_scan_failed,
    premium_required,
)
from app.core.redis import get_redis
from app.models.user import User, UserProfile
from app.schemas.common import APIResponse
from app.schemas.meal import MealDetailResponse, MealHistoryResponse, MealItemUpdate, MealScanResponse
from app.schemas.nutrition import FoodItemResponse, NutrientInfo
from app.services import meal_service
from app.services.ai_food_recognizer import AIFoodRecognizer
from app.services.image_storage import upload_image
from app.services.nutrition_lookup import NutritionLookup
from app.services.recommendation_engine import generate_recommendations
from app.utils.constants import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES
from app.utils.helpers import get_today_utc, parse_date

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meals", tags=["Meals"])


@router.post("/scan", response_model=APIResponse[MealScanResponse], status_code=201)
async def scan_meal(
    image: UploadFile = File(..., description="Food photo (JPEG/PNG/WebP, max 10MB)"),
    meal_type: str = Form(default="snack", description="breakfast, lunch, dinner, snack"),
    notes: str = Form(default=""),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> APIResponse[MealScanResponse]:
    """
    Core endpoint: upload a food photo → AI identifies items → nutrition analysis → save.

    Flow:
    1. Validate image
    2. Check premium scan limit (3/day for free users)
    3. Upload to Cloudflare R2 (optional — gracefully skipped if not configured)
    4. AI food recognition (Gemini → OpenRouter fallback)
    5. Nutrition lookup per item (Redis → DB cache → USDA → AI fallback)
    6. Save meal to database
    7. Generate personalized recommendations
    8. Return full analysis
    """
    # ── 1. Validate image ────────────────────────────────────────────────────
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise meal_image_invalid()

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise meal_image_too_large()

    # ── 2. Premium gate ──────────────────────────────────────────────────────
    if not current_user.is_premium:
        from app.core.config import get_settings
        settings = get_settings()
        today_count = await meal_service.count_today_scans(current_user.id, db)
        if today_count >= settings.free_daily_scan_limit:
            raise premium_required()

    # ── 3. Upload to R2 ──────────────────────────────────────────────────────
    image_url = await upload_image(str(current_user.id), image_bytes, image.content_type)

    # ── 4. AI recognition ────────────────────────────────────────────────────
    recognizer = AIFoodRecognizer()
    recognition = await recognizer.analyze_food_image(image_bytes, image.content_type)

    raw_food_items = recognition.get("food_items", [])
    if not raw_food_items:
        raise meal_scan_failed()

    ai_provider = recognition.get("_ai_provider", "unknown")
    ai_model = recognition.get("_ai_model", "unknown")

    # ── 5. Nutrition estimation ──────────────────────────────────────────────
    nutrition_result = await recognizer.estimate_nutrition(raw_food_items)
    nutrition_items = nutrition_result.get("food_items", []) if nutrition_result else raw_food_items

    nutrition_service = NutritionLookup()
    enriched_items: list[dict] = []

    for item in nutrition_items:
        weight_g = item.get("estimated_weight_g", 100)
        # Get nutrition via 3-tier cache (Redis → DB → USDA → AI)
        nutrition = await nutrition_service.get_nutrition_with_cache(
            food_name=item["name"],
            weight_g=weight_g,
            ai_estimate=item,
            redis=redis,
            db=db,
        )

        # Match confidence from recognition step
        orig = next(
            (r for r in raw_food_items if r["name"].lower() == item["name"].lower()),
            raw_food_items[0] if raw_food_items else {},
        )

        enriched_items.append({
            "name": item["name"],
            "confidence": orig.get("confidence", 0.8),
            "estimated_portion": orig.get("estimated_portion", "1 serving"),
            "estimated_weight_g": weight_g,
            "calories": nutrition.get("calories", item.get("calories", 0)),
            "protein_g": nutrition.get("protein_g", item.get("protein_g", 0)),
            "carbs_g": nutrition.get("carbs_g", item.get("carbs_g", 0)),
            "fat_g": nutrition.get("fat_g", item.get("fat_g", 0)),
            "fiber_g": nutrition.get("fiber_g", item.get("fiber_g", 0)),
            "vitamins": nutrition.get("vitamins", {}),
            "minerals": nutrition.get("minerals", {}),
        })

    # ── 6. Save to database ──────────────────────────────────────────────────
    meal = await meal_service.create_meal(
        user_id=current_user.id,
        meal_type=meal_type,
        food_items_data=enriched_items,
        ai_provider=ai_provider,
        ai_model=ai_model,
        image_url=image_url,
        notes=notes or None,
        db=db,
    )

    # ── 7. Build food item responses and generate recommendations ────────────
    food_item_responses = []
    all_vitamins: dict = {}
    all_minerals: dict = {}

    for item_data in enriched_items:
        vitamins = [
            NutrientInfo(name=k, amount=v["amount"], unit=v["unit"], daily_value_percent=v.get("dv_percent"))
            for k, v in item_data.get("vitamins", {}).items()
        ]
        minerals = [
            NutrientInfo(name=k, amount=v["amount"], unit=v["unit"], daily_value_percent=v.get("dv_percent"))
            for k, v in item_data.get("minerals", {}).items()
        ]

        food_item_responses.append(
            FoodItemResponse(
                id=str(uuid.uuid4()),  # temp display ID
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
                all_vitamins[v.name] = {"amount": v.amount, "unit": v.unit, "dvp": v.daily_value_percent or 0}
            else:
                all_vitamins[v.name]["amount"] += v.amount

        for m in minerals:
            if m.name not in all_minerals:
                all_minerals[m.name] = {"amount": m.amount, "unit": m.unit, "dvp": m.daily_value_percent or 0}
            else:
                all_minerals[m.name]["amount"] += m.amount

    # Detect low nutrients (below 50% DV)
    low_nutrients = [name for name, d in {**all_vitamins, **all_minerals}.items() if d["dvp"] < 50]

    # Generate recommendations if user has a profile
    recommendations: list[str] = []
    try:
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            recommendations = generate_recommendations(
                calories_consumed=meal.total_calories,
                protein_consumed=meal.total_protein_g,
                calorie_target=profile.daily_calorie_target,
                protein_target=profile.daily_protein_target_g,
                low_nutrients=low_nutrients,
            )
    except Exception as exc:
        logger.warning(f"Failed to generate recommendations: {exc}")

    vitamins_summary = [
        NutrientInfo(name=n, amount=round(d["amount"], 1), unit=d["unit"], daily_value_percent=round(d["dvp"], 1))
        for n, d in all_vitamins.items()
    ]
    minerals_summary = [
        NutrientInfo(name=n, amount=round(d["amount"], 1), unit=d["unit"], daily_value_percent=round(d["dvp"], 1))
        for n, d in all_minerals.items()
    ]

    return APIResponse.ok(
        MealScanResponse(
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
    )


@router.get("/history", response_model=APIResponse[MealHistoryResponse])
async def get_meal_history(
    date: str = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MealHistoryResponse]:
    """
    Get meal history for a specific date.

    Query params:
      - date: YYYY-MM-DD (defaults to today)
    """
    target_date = parse_date(date) if date else get_today_utc()
    history = await meal_service.get_meal_history(current_user.id, target_date, db)
    return APIResponse.ok(history)


@router.get("/{meal_id}", response_model=APIResponse[MealDetailResponse])
async def get_meal(
    meal_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MealDetailResponse]:
    """Get full details for a specific meal."""
    meal = await meal_service.get_meal(meal_id, current_user.id, db)
    return APIResponse.ok(meal_service.build_meal_detail_response(meal))


@router.patch("/{meal_id}/items/{item_id}", response_model=APIResponse[MealDetailResponse])
async def update_meal_item(
    meal_id: uuid.UUID,
    item_id: uuid.UUID,
    data: MealItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MealDetailResponse]:
    """
    Manually correct a food item in a meal.
    Also recalculates the meal's total nutrition.
    """
    meal = await meal_service.update_meal_item(meal_id, item_id, current_user.id, data, db)
    return APIResponse.ok(meal_service.build_meal_detail_response(meal))


@router.delete("/{meal_id}", response_model=APIResponse[dict], status_code=200)
async def delete_meal(
    meal_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Delete a meal and all its food items."""
    await meal_service.delete_meal(meal_id, current_user.id, db)
    return APIResponse.ok({"deleted": str(meal_id)})
