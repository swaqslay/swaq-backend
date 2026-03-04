#!/usr/bin/env python3
"""
Seed common Indian foods into the nutrition_cache table.
Avoids USDA misses for popular desi dishes.

Run: python scripts/seed_indian_foods.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

INDIAN_FOODS = [
    {
        "name": "dal tadka",
        "per_100g": {"calories": 91, "protein_g": 5.5, "fat_g": 2.8, "carbs_g": 11.5, "fiber_g": 2.2},
        "vitamins": {"folate": {"amount": 45, "unit": "mcg", "dv_percent": 11.3}},
        "minerals": {
            "iron": {"amount": 1.8, "unit": "mg", "dv_percent": 10.0},
            "potassium": {"amount": 250, "unit": "mg", "dv_percent": 5.3},
        },
    },
    {
        "name": "roti",
        "per_100g": {"calories": 297, "protein_g": 9.0, "fat_g": 3.5, "carbs_g": 55.0, "fiber_g": 2.5},
        "vitamins": {"vitamin_b6": {"amount": 0.18, "unit": "mg", "dv_percent": 10.6}},
        "minerals": {"iron": {"amount": 3.0, "unit": "mg", "dv_percent": 16.7}},
    },
    {
        "name": "chicken biryani",
        "per_100g": {"calories": 185, "protein_g": 10.5, "fat_g": 7.2, "carbs_g": 19.8, "fiber_g": 0.8},
        "vitamins": {"vitamin_b12": {"amount": 0.5, "unit": "mcg", "dv_percent": 20.8}},
        "minerals": {
            "iron": {"amount": 1.2, "unit": "mg", "dv_percent": 6.7},
            "zinc": {"amount": 1.5, "unit": "mg", "dv_percent": 13.6},
        },
    },
    {
        "name": "paneer",
        "per_100g": {"calories": 265, "protein_g": 18.3, "fat_g": 20.8, "carbs_g": 1.2, "fiber_g": 0.0},
        "vitamins": {
            "vitamin_a": {"amount": 120, "unit": "mcg", "dv_percent": 13.3},
            "vitamin_b12": {"amount": 0.8, "unit": "mcg", "dv_percent": 33.3},
        },
        "minerals": {
            "calcium": {"amount": 480, "unit": "mg", "dv_percent": 36.9},
            "phosphorus": {"amount": 320, "unit": "mg", "dv_percent": 25.6},
        },
    },
    {
        "name": "idli",
        "per_100g": {"calories": 58, "protein_g": 2.0, "fat_g": 0.4, "carbs_g": 12.0, "fiber_g": 0.5},
        "vitamins": {"folate": {"amount": 12, "unit": "mcg", "dv_percent": 3.0}},
        "minerals": {"iron": {"amount": 0.8, "unit": "mg", "dv_percent": 4.4}},
    },
    {
        "name": "dosa",
        "per_100g": {"calories": 168, "protein_g": 3.9, "fat_g": 4.2, "carbs_g": 28.1, "fiber_g": 1.0},
        "vitamins": {"folate": {"amount": 18, "unit": "mcg", "dv_percent": 4.5}},
        "minerals": {"iron": {"amount": 1.0, "unit": "mg", "dv_percent": 5.6}},
    },
    {
        "name": "sambar",
        "per_100g": {"calories": 56, "protein_g": 2.8, "fat_g": 1.5, "carbs_g": 7.8, "fiber_g": 2.0},
        "vitamins": {
            "vitamin_c": {"amount": 8.5, "unit": "mg", "dv_percent": 9.4},
            "folate": {"amount": 25, "unit": "mcg", "dv_percent": 6.3},
        },
        "minerals": {"iron": {"amount": 1.2, "unit": "mg", "dv_percent": 6.7}},
    },
    {
        "name": "chole",
        "per_100g": {"calories": 132, "protein_g": 7.2, "fat_g": 2.8, "carbs_g": 19.5, "fiber_g": 5.3},
        "vitamins": {"folate": {"amount": 55, "unit": "mcg", "dv_percent": 13.8}},
        "minerals": {
            "iron": {"amount": 2.8, "unit": "mg", "dv_percent": 15.6},
            "zinc": {"amount": 1.2, "unit": "mg", "dv_percent": 10.9},
        },
    },
    {
        "name": "rajma",
        "per_100g": {"calories": 127, "protein_g": 8.7, "fat_g": 0.5, "carbs_g": 22.8, "fiber_g": 7.4},
        "vitamins": {"folate": {"amount": 68, "unit": "mcg", "dv_percent": 17.0}},
        "minerals": {
            "iron": {"amount": 2.9, "unit": "mg", "dv_percent": 16.1},
            "potassium": {"amount": 403, "unit": "mg", "dv_percent": 8.6},
        },
    },
    {
        "name": "aloo paratha",
        "per_100g": {"calories": 218, "protein_g": 5.5, "fat_g": 8.2, "carbs_g": 30.8, "fiber_g": 1.8},
        "vitamins": {"vitamin_b6": {"amount": 0.22, "unit": "mg", "dv_percent": 12.9}},
        "minerals": {
            "iron": {"amount": 1.5, "unit": "mg", "dv_percent": 8.3},
            "potassium": {"amount": 310, "unit": "mg", "dv_percent": 6.6},
        },
    },
]


async def seed():
    from app.core.database import async_session, init_db
    from app.models.nutrition_cache import NutritionCache
    from app.utils.helpers import normalize_food_name
    from sqlalchemy import select

    await init_db()

    async with async_session() as session:
        count = 0
        for food in INDIAN_FOODS:
            normalized = normalize_food_name(food["name"])
            result = await session.execute(
                select(NutritionCache).where(NutritionCache.food_name_normalized == normalized)
            )
            if result.scalar_one_or_none():
                print(f"  skip (exists): {food['name']}")
                continue

            data = {
                "per_100g": food["per_100g"],
                "vitamins": food.get("vitamins", {}),
                "minerals": food.get("minerals", {}),
            }
            session.add(NutritionCache(
                food_name_normalized=normalized,
                nutrition_data=data,
                source="ifct",
            ))
            count += 1
            print(f"  seeded: {food['name']}")

        await session.commit()
        print(f"\nSeeded {count} Indian foods into nutrition_cache.")


if __name__ == "__main__":
    asyncio.run(seed())
