"""
Nutrition lookup service — three-tier lookup pipeline:
  Tier 1: Redis cache   (~1ms)
  Tier 2: PostgreSQL nutrition_cache table   (~5ms)
  Tier 3: USDA FoodData Central API → AI estimate fallback   (~200-500ms)
"""

import json
import logging
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.nutrition_cache import NutritionCache
from app.utils.constants import (
    DAILY_VALUES,
    REDIS_TTL_NUTRITION,
    REDIS_TTL_USDA_SEARCH,
    USDA_NUTRIENT_IDS,
)
from app.utils.helpers import normalize_food_name

logger = logging.getLogger(__name__)
settings = get_settings()

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

# Vitamin/mineral keys and their USDA nutrient IDs
VITAMIN_KEYS = ["vitamin_a", "vitamin_c", "vitamin_d", "vitamin_b6", "vitamin_b12", "folate", "vitamin_e"]
MINERAL_KEYS = ["calcium", "iron", "magnesium", "potassium", "sodium", "zinc"]


class NutritionLookup:
    """
    Three-tier nutrition lookup: Redis → PostgreSQL cache → USDA API → AI fallback.
    """

    def __init__(self):
        self.api_key = settings.usda_api_key

    async def get_nutrition_with_cache(
        self,
        food_name: str,
        weight_g: float,
        ai_estimate: dict,
        redis=None,
        db: Optional[AsyncSession] = None,
    ) -> dict:
        """
        Get nutrition data for a food item using the three-tier lookup.

        Args:
            food_name: Human-readable food name.
            weight_g: Estimated weight of the portion in grams.
            ai_estimate: AI-estimated nutrition dict (fallback if all else fails).
            redis: Redis client (optional — degrades gracefully).
            db: AsyncSession (optional — needed for PostgreSQL cache tier).

        Returns:
            Nutrition dict with calories, macros, vitamins, minerals per portion.
        """
        normalized = normalize_food_name(food_name)
        cache_key = f"nutrition:{normalized}"

        # ── Tier 1: Redis ────────────────────────────────────────────────────
        if redis:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    logger.debug(f"Redis cache hit: {food_name}")
                    data = json.loads(cached)
                    return self._scale_to_portion(data, weight_g)
            except Exception as exc:
                logger.warning(f"Redis get failed: {exc}")

        # ── Tier 2: PostgreSQL cache ─────────────────────────────────────────
        if db:
            try:
                result = await db.execute(
                    select(NutritionCache).where(NutritionCache.food_name_normalized == normalized)
                )
                cached_row = result.scalar_one_or_none()
                if cached_row:
                    logger.debug(f"DB cache hit: {food_name}")
                    # Re-warm Redis
                    if redis:
                        try:
                            await redis.set(cache_key, json.dumps(cached_row.nutrition_data), ex=REDIS_TTL_NUTRITION)
                        except Exception:
                            pass
                    return self._scale_to_portion(cached_row.nutrition_data, weight_g)
            except Exception as exc:
                logger.warning(f"DB cache lookup failed: {exc}")

        # ── Tier 3: USDA API ─────────────────────────────────────────────────
        usda_data = await self._fetch_from_usda(food_name)

        if usda_data:
            source = "usda"
            fdc_id = usda_data.get("fdc_id")
        else:
            # Fallback to AI estimate (convert to per-100g format)
            logger.info(f"USDA miss for '{food_name}', using AI estimate")
            usda_data = self._ai_estimate_to_per_100g(ai_estimate, weight_g)
            source = "ai_estimated"
            fdc_id = None

        # Store in both caches
        await self._store_in_cache(normalized, usda_data, fdc_id, source, redis, db)

        return self._scale_to_portion(usda_data, weight_g)

    async def _fetch_from_usda(self, food_name: str) -> Optional[dict]:
        """Search USDA and get detailed nutrients for the best match."""
        if not self.api_key:
            return None

        foods = await self.search_food(food_name, max_results=3)
        if not foods:
            return None

        # Get detailed nutrients for top match
        best_fdc_id = foods[0]["fdc_id"]
        return await self.get_food_nutrients(best_fdc_id)

    async def search_food(self, food_name: str, max_results: int = 5) -> list[dict]:
        """Search USDA FoodData Central for a food item."""
        url = f"{USDA_BASE_URL}/foods/search"
        params = {
            "api_key": self.api_key,
            "query": food_name,
            "pageSize": max_results,
            "dataType": ["Foundation", "SR Legacy"],
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            return [
                {
                    "fdc_id": food["fdcId"],
                    "description": food["description"],
                }
                for food in data.get("foods", [])
            ]
        except Exception as exc:
            logger.error(f"USDA search failed for '{food_name}': {exc}")
            return []

    async def get_food_nutrients(self, fdc_id: int) -> Optional[dict]:
        """Get full nutrient profile for a USDA food by FDC ID (per 100g)."""
        url = f"{USDA_BASE_URL}/food/{fdc_id}"
        params = {"api_key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            # Build nutrient_id → {name, amount, unit} map
            nutrient_map: dict[int, dict] = {}
            for n in data.get("foodNutrients", []):
                nutrient = n.get("nutrient", {})
                nid = nutrient.get("id")
                if nid:
                    nutrient_map[nid] = {
                        "name": nutrient.get("name", ""),
                        "amount": n.get("amount", 0),
                        "unit": nutrient.get("unitName", ""),
                    }

            def get_amt(key: str) -> float:
                return nutrient_map.get(USDA_NUTRIENT_IDS.get(key, 0), {}).get("amount", 0)

            result = {
                "fdc_id": fdc_id,
                "description": data.get("description", ""),
                "per_100g": {
                    "calories": get_amt("calories"),
                    "protein_g": get_amt("protein"),
                    "fat_g": get_amt("fat"),
                    "carbs_g": get_amt("carbs"),
                    "fiber_g": get_amt("fiber"),
                },
                "vitamins": {},
                "minerals": {},
            }

            for key in VITAMIN_KEYS:
                nid = USDA_NUTRIENT_IDS.get(key)
                if nid and nid in nutrient_map:
                    n = nutrient_map[nid]
                    dv = DAILY_VALUES.get(f"{key}_mg") or DAILY_VALUES.get(f"{key}_mcg")
                    result["vitamins"][key] = {
                        "amount": n["amount"],
                        "unit": n["unit"].lower(),
                        "dv_percent": round(n["amount"] / dv * 100, 1) if dv else None,
                    }

            for key in MINERAL_KEYS:
                nid = USDA_NUTRIENT_IDS.get(key)
                if nid and nid in nutrient_map:
                    n = nutrient_map[nid]
                    dv = DAILY_VALUES.get(f"{key}_mg")
                    result["minerals"][key] = {
                        "amount": n["amount"],
                        "unit": n["unit"].lower(),
                        "dv_percent": round(n["amount"] / dv * 100, 1) if dv else None,
                    }

            return result

        except Exception as exc:
            logger.error(f"USDA detail fetch failed for FDC {fdc_id}: {exc}")
            return None

    @staticmethod
    def _ai_estimate_to_per_100g(ai_estimate: dict, weight_g: float) -> dict:
        """Convert an AI-estimated nutrition dict (for portion) to per-100g format."""
        factor = 100.0 / max(weight_g, 1)
        vitamins = {}
        for v in ai_estimate.get("vitamins", []):
            key = v["name"].lower().replace(" ", "_")
            vitamins[key] = {
                "amount": round(v.get("amount", 0) * factor, 3),
                "unit": v.get("unit", "mg"),
                "dv_percent": v.get("daily_value_percent"),
            }
        minerals = {}
        for m in ai_estimate.get("minerals", []):
            key = m["name"].lower().replace(" ", "_")
            minerals[key] = {
                "amount": round(m.get("amount", 0) * factor, 3),
                "unit": m.get("unit", "mg"),
                "dv_percent": m.get("daily_value_percent"),
            }
        return {
            "per_100g": {
                "calories": round(ai_estimate.get("calories", 0) * factor, 1),
                "protein_g": round(ai_estimate.get("protein_g", 0) * factor, 1),
                "fat_g": round(ai_estimate.get("fat_g", 0) * factor, 1),
                "carbs_g": round(ai_estimate.get("carbs_g", 0) * factor, 1),
                "fiber_g": round(ai_estimate.get("fiber_g", 0) * factor, 1),
            },
            "vitamins": vitamins,
            "minerals": minerals,
        }

    @staticmethod
    def _scale_to_portion(per_100g_data: dict, weight_g: float) -> dict:
        """Scale per-100g nutrition data to the actual portion weight."""
        factor = weight_g / 100.0
        base = per_100g_data.get("per_100g", {})
        result = {
            "calories": round(base.get("calories", 0) * factor, 1),
            "protein_g": round(base.get("protein_g", 0) * factor, 1),
            "fat_g": round(base.get("fat_g", 0) * factor, 1),
            "carbs_g": round(base.get("carbs_g", 0) * factor, 1),
            "fiber_g": round(base.get("fiber_g", 0) * factor, 1),
            "vitamins": {},
            "minerals": {},
        }
        for key, v in per_100g_data.get("vitamins", {}).items():
            result["vitamins"][key] = {
                "amount": round(v.get("amount", 0) * factor, 2),
                "unit": v.get("unit", "mg"),
                "dv_percent": round(v.get("dv_percent", 0) * factor, 1) if v.get("dv_percent") else None,
            }
        for key, m in per_100g_data.get("minerals", {}).items():
            result["minerals"][key] = {
                "amount": round(m.get("amount", 0) * factor, 2),
                "unit": m.get("unit", "mg"),
                "dv_percent": round(m.get("dv_percent", 0) * factor, 1) if m.get("dv_percent") else None,
            }
        return result

    async def _store_in_cache(
        self,
        normalized_name: str,
        data: dict,
        fdc_id: Optional[int],
        source: str,
        redis,
        db: Optional[AsyncSession],
    ) -> None:
        """Store nutrition data in Redis and PostgreSQL cache."""
        cache_key = f"nutrition:{normalized_name}"

        if redis:
            try:
                await redis.set(cache_key, json.dumps(data), ex=REDIS_TTL_NUTRITION)
            except Exception as exc:
                logger.warning(f"Redis set failed: {exc}")

        if db:
            try:
                # Upsert — update if exists, insert if not
                result = await db.execute(
                    select(NutritionCache).where(NutritionCache.food_name_normalized == normalized_name)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.nutrition_data = data
                    existing.source = source
                    if fdc_id:
                        existing.usda_fdc_id = fdc_id
                else:
                    db.add(NutritionCache(
                        food_name_normalized=normalized_name,
                        usda_fdc_id=fdc_id,
                        nutrition_data=data,
                        source=source,
                    ))
                await db.flush()
            except Exception as exc:
                logger.warning(f"DB cache store failed: {exc}")
