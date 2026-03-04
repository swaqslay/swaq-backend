"""Tests for nutrition utilities: normalization and scaling."""

import pytest
from app.utils.helpers import normalize_food_name
from app.services.nutrition_lookup import NutritionLookup


def test_normalize_basic():
    assert normalize_food_name("  Chicken Biryani  ") == "chicken biryani"


def test_normalize_removes_special_chars():
    assert normalize_food_name("dal-tadka!") == "dal tadka"


def test_normalize_collapses_spaces():
    assert normalize_food_name("aloo  gobi") == "aloo gobi"


def test_normalize_lowercase():
    assert normalize_food_name("PANEER TIKKA") == "paneer tikka"


def test_scale_nutrients_100g():
    service = NutritionLookup()
    per_100g = {
        "per_100g": {"calories": 200, "protein_g": 10, "fat_g": 5, "carbs_g": 25, "fiber_g": 2},
        "vitamins": {},
        "minerals": {},
    }
    scaled = service._scale_to_portion(per_100g, 100)
    assert scaled["calories"] == 200
    assert scaled["protein_g"] == 10


def test_scale_nutrients_half_portion():
    service = NutritionLookup()
    per_100g = {
        "per_100g": {"calories": 200, "protein_g": 10, "fat_g": 5, "carbs_g": 25, "fiber_g": 2},
        "vitamins": {},
        "minerals": {},
    }
    scaled = service._scale_to_portion(per_100g, 50)
    assert scaled["calories"] == 100
    assert scaled["protein_g"] == 5


def test_scale_nutrients_double_portion():
    service = NutritionLookup()
    per_100g = {
        "per_100g": {"calories": 100, "protein_g": 5, "fat_g": 2, "carbs_g": 15, "fiber_g": 1},
        "vitamins": {"vitamin_c": {"amount": 20, "unit": "mg", "dv_percent": 22.2}},
        "minerals": {},
    }
    scaled = service._scale_to_portion(per_100g, 200)
    assert scaled["calories"] == 200
    assert scaled["vitamins"]["vitamin_c"]["amount"] == 40


def test_ai_estimate_to_per_100g():
    service = NutritionLookup()
    ai_data = {
        "calories": 150,
        "protein_g": 8,
        "fat_g": 3,
        "carbs_g": 20,
        "fiber_g": 2,
        "vitamins": [{"name": "Vitamin C", "amount": 15, "unit": "mg", "daily_value_percent": 16.7}],
        "minerals": [],
    }
    per_100g = service._ai_estimate_to_per_100g(ai_data, weight_g=150)
    # 150g portion → per 100g should be ÷1.5
    assert per_100g["per_100g"]["calories"] == pytest.approx(100, abs=1)
    assert per_100g["per_100g"]["protein_g"] == pytest.approx(5.33, abs=0.1)
