"""
ARQ worker for async meal scanning.

Contains the process_meal_scan task and Redis scan state helpers.
Run separately: arq app.services.scan_worker.WorkerSettings
"""

import asyncio
import base64
import json
import logging
import traceback
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Redis scan state helpers ─────────────────────────────────────────────────

SCAN_KEY_PREFIX = "scan:"
SCAN_TTL_SECONDS = 3600  # 1 hour


async def set_scan_state(redis: object, scan_id: str, state: dict) -> None:
    """Store scan state in Redis with TTL."""
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    await redis.set(
        f"{SCAN_KEY_PREFIX}{scan_id}",
        json.dumps(state),
        ex=SCAN_TTL_SECONDS,
    )


async def get_scan_state(redis: object, scan_id: str) -> dict | None:
    """Retrieve scan state from Redis."""
    data = await redis.get(f"{SCAN_KEY_PREFIX}{scan_id}")
    if data is None:
        return None
    return json.loads(data)


# ── ARQ task ─────────────────────────────────────────────────────────────────


async def process_meal_scan(
    ctx: dict,
    scan_id: str,
    image_bytes_b64: str,
    content_type: str,
    user_id: str,
    meal_type: str,
    notes: str | None,
    image_url: str | None,
) -> None:
    """
    ARQ task: process a meal scan in the background.

    Steps:
    1. Set status to processing
    2. Run AI food recognition
    3. Estimate nutrition per item
    4. Save meal to database
    5. Generate recommendations
    6. Set status to completed with result
    """
    # Lazy imports to avoid circular dependencies
    from sqlalchemy import select

    from app.models.user import UserProfile
    from app.schemas.meal import MealScanResponse
    from app.schemas.nutrition import FoodItemResponse, NutrientInfo
    from app.services import meal_service
    from app.services.ai_food_recognizer import AIFoodRecognizer
    from app.services.nutrition_lookup import NutritionLookup
    from app.services.recommendation_engine import generate_recommendations

    redis = ctx["redis"]

    # Set status to processing
    current_state = await get_scan_state(redis, scan_id)
    if current_state:
        current_state["status"] = "processing"
        await set_scan_state(redis, scan_id, current_state)

    # Get a DB session from the factory
    session_factory = ctx["session_factory"]
    db = session_factory()

    try:
        # Decode image bytes
        image_bytes = base64.b64decode(image_bytes_b64)

        # AI recognition + nutrition (combined single call)
        recognizer = AIFoodRecognizer()
        recognition = await recognizer.analyze_food_image_with_nutrition(
            image_bytes, content_type
        )

        raw_food_items = recognition.get("food_items", [])
        if not raw_food_items:
            await set_scan_state(
                redis,
                scan_id,
                {
                    "status": "failed",
                    "user_id": user_id,
                    "meal_type": meal_type,
                    "image_url": image_url,
                    "meal_id": None,
                    "result": None,
                    "error": json.dumps(
                        {
                            "code": "MEAL_SCAN_FAILED",
                            "message": "Could not identify any food items in the image.",
                        }
                    ),
                },
            )
            return

        ai_provider = recognition.get("_ai_provider", "unknown")
        ai_model = recognition.get("_ai_model", "unknown")

        # Combined result already has nutrition in food_items
        nutrition_items = raw_food_items

        nutrition_service = NutritionLookup()

        # Parallel USDA lookups — each uses Redis cache (thread-safe)
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

        enriched_items: list[dict] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Nutrition lookup failed for an item: {result}")
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

        # Save to database
        user_uuid = uuid.UUID(user_id)
        meal = await meal_service.create_meal(
            user_id=user_uuid,
            meal_type=meal_type,
            food_items_data=enriched_items,
            ai_provider=ai_provider,
            ai_model=ai_model,
            image_url=image_url,
            notes=notes,
            db=db,
        )
        await db.commit()

        # Build response objects
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

        # Detect low nutrients
        low_nutrients = [
            name for name, d in {**all_vitamins, **all_minerals}.items() if d["dvp"] < 50
        ]

        # Generate recommendations if user has a profile
        recommendations: list[str] = []
        try:
            result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_uuid))
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

        scan_response = MealScanResponse(
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

        # Set completed state
        await set_scan_state(
            redis,
            scan_id,
            {
                "status": "completed",
                "user_id": user_id,
                "meal_type": meal_type,
                "image_url": image_url,
                "meal_id": str(meal.id),
                "result": scan_response.model_dump_json(),
                "error": None,
            },
        )

    except Exception as exc:
        logger.error("Scan %s failed: %s\n%s", scan_id, exc, traceback.format_exc())
        await db.rollback()
        await set_scan_state(
            redis,
            scan_id,
            {
                "status": "failed",
                "user_id": user_id,
                "meal_type": meal_type,
                "image_url": image_url,
                "meal_id": None,
                "result": None,
                "error": json.dumps(
                    {
                        "code": "SCAN_PROCESSING_FAILED",
                        "message": str(exc),
                    }
                ),
            },
        )
    finally:
        for obj_name in ("recognizer", "nutrition_service"):
            try:
                obj = locals().get(obj_name)
                if obj and hasattr(obj, "close"):
                    await obj.close()
            except Exception:
                pass
        await db.close()


# ── ARQ WorkerSettings ───────────────────────────────────────────────────────


class WorkerSettings:
    """ARQ worker configuration. Run: arq app.services.scan_worker.WorkerSettings"""

    functions = [process_meal_scan]
    job_timeout = 120
    max_jobs = 10
    poll_delay = 0.5

    @staticmethod
    async def on_startup(ctx: dict) -> None:
        """Initialize DB engine and Redis for the worker context."""
        import redis.asyncio as aioredis

        from app.core.config import get_settings
        from app.core.database import get_async_session_factory

        settings = get_settings()
        ctx["redis"] = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        ctx["session_factory"] = get_async_session_factory()

    @staticmethod
    async def on_shutdown(ctx: dict) -> None:
        """Cleanup worker context."""
        if "redis" in ctx:
            await ctx["redis"].aclose()
