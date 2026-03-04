"""
Meal Scanning API Endpoints

POST /api/meals/scan    - Upload food photo, get full nutrition analysis
GET  /api/meals/history - Get meal history for a date range
GET  /api/meals/{id}    - Get details of a specific meal
"""

import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models.nutrition import MealAnalysis, FoodItem, NutrientInfo
from app.services.ai_food_recognizer import AIFoodRecognizer
from app.services.nutrition_lookup import NutritionLookup

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/meals", tags=["Meals"])

# Service instances
ai_recognizer = AIFoodRecognizer()
nutrition_service = NutritionLookup()


@router.post("/scan", response_model=MealAnalysis)
async def scan_meal(
    image: UploadFile = File(..., description="Food photo (JPEG/PNG, max 10MB)"),
    meal_type: str = Form(default="snack", description="breakfast, lunch, dinner, snack"),
    notes: str = Form(default="", description="Optional notes about the meal"),
):
    """
    Upload a food photo and get complete nutrition analysis.

    This is the core endpoint of the app. It:
    1. Sends the image to AI (Gemini/OpenRouter) for food identification
    2. Estimates nutrition for each identified food item
    3. Returns calories, macros, vitamins, and minerals breakdown

    The AI automatically falls back from Gemini → OpenRouter if needed.
    """
    # Validate file
    if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(400, "Only JPEG, PNG, and WebP images are supported.")

    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "Image must be under 10MB.")

    # Step 1: AI Food Recognition
    logger.info(f"Scanning meal photo ({len(image_bytes)} bytes)...")
    recognition_result = await ai_recognizer.analyze_food_image(
        image_bytes, mime_type=image.content_type
    )

    if not recognition_result or "food_items" not in recognition_result:
        raise HTTPException(422, "Could not identify any food items in the image.")

    ai_provider = recognition_result.get("_ai_provider", "unknown")
    ai_model = recognition_result.get("_ai_model", "unknown")

    # Step 2: Get detailed nutrition for identified items
    # First try AI-based estimation (works for all cuisines including Indian)
    logger.info(f"Estimating nutrition for {len(recognition_result['food_items'])} items...")
    nutrition_result = await ai_recognizer.estimate_nutrition(recognition_result["food_items"])

    # Step 3: Build response with full breakdown
    food_items = []
    total_cal = total_protein = total_carbs = total_fat = total_fiber = 0
    all_vitamins = {}
    all_minerals = {}

    nutrition_items = nutrition_result.get("food_items", []) if nutrition_result else []

    for item in nutrition_items:
        # Build vitamin list
        vitamins = [
            NutrientInfo(
                name=v["name"],
                amount=v.get("amount", 0),
                unit=v.get("unit", "mg"),
                daily_value_percent=v.get("daily_value_percent"),
            )
            for v in item.get("vitamins", [])
        ]

        # Build mineral list
        minerals = [
            NutrientInfo(
                name=m["name"],
                amount=m.get("amount", 0),
                unit=m.get("unit", "mg"),
                daily_value_percent=m.get("daily_value_percent"),
            )
            for m in item.get("minerals", [])
        ]

        # Accumulate totals for vitamins and minerals
        for v in vitamins:
            if v.name in all_vitamins:
                all_vitamins[v.name]["amount"] += v.amount
                if v.daily_value_percent:
                    all_vitamins[v.name]["dvp"] = all_vitamins[v.name].get("dvp", 0) + v.daily_value_percent
            else:
                all_vitamins[v.name] = {"amount": v.amount, "unit": v.unit, "dvp": v.daily_value_percent or 0}

        for m in minerals:
            if m.name in all_minerals:
                all_minerals[m.name]["amount"] += m.amount
                if m.daily_value_percent:
                    all_minerals[m.name]["dvp"] = all_minerals[m.name].get("dvp", 0) + m.daily_value_percent
            else:
                all_minerals[m.name] = {"amount": m.amount, "unit": m.unit, "dvp": m.daily_value_percent or 0}

        # Find matching recognition item for confidence score
        orig_item = next(
            (r for r in recognition_result["food_items"] if r["name"].lower() == item["name"].lower()),
            recognition_result["food_items"][0] if recognition_result["food_items"] else {"confidence": 0.8, "estimated_portion": "1 serving"}
        )

        food_item = FoodItem(
            name=item["name"],
            confidence=orig_item.get("confidence", 0.8),
            estimated_portion=orig_item.get("estimated_portion", "1 serving"),
            estimated_weight_g=item.get("estimated_weight_g", 100),
            calories=item.get("calories", 0),
            protein_g=item.get("protein_g", 0),
            carbs_g=item.get("carbs_g", 0),
            fat_g=item.get("fat_g", 0),
            fiber_g=item.get("fiber_g", 0),
            vitamins=vitamins,
            minerals=minerals,
        )
        food_items.append(food_item)

        # Accumulate macros
        total_cal += food_item.calories
        total_protein += food_item.protein_g
        total_carbs += food_item.carbs_g
        total_fat += food_item.fat_g
        total_fiber += food_item.fiber_g

    # Build vitamin/mineral summaries
    vitamins_summary = [
        NutrientInfo(name=name, amount=round(data["amount"], 1), unit=data["unit"], daily_value_percent=round(data["dvp"], 1))
        for name, data in all_vitamins.items()
    ]
    minerals_summary = [
        NutrientInfo(name=name, amount=round(data["amount"], 1), unit=data["unit"], daily_value_percent=round(data["dvp"], 1))
        for name, data in all_minerals.items()
    ]

    return MealAnalysis(
        meal_id=str(uuid.uuid4()),
        food_items=food_items,
        total_calories=round(total_cal, 1),
        total_protein_g=round(total_protein, 1),
        total_carbs_g=round(total_carbs, 1),
        total_fat_g=round(total_fat, 1),
        total_fiber_g=round(total_fiber, 1),
        vitamins_summary=vitamins_summary,
        minerals_summary=minerals_summary,
        ai_provider=ai_provider,
        ai_model=ai_model,
        analyzed_at=datetime.utcnow(),
    )


@router.get("/history")
async def get_meal_history(date: str = None):
    """Get meal history. Placeholder - will connect to DB."""
    return {
        "message": "Meal history endpoint - connect to database",
        "date": date or "today",
        "meals": [],
    }
