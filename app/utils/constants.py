"""
Shared constants: RDA values, activity multipliers, goal adjustments.
Single source of truth — imported by all services.
"""

# Free tier scan limit per day
FREE_DAILY_SCAN_LIMIT = 3

# Activity level multipliers for TDEE (Mifflin-St Jeor)
ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,  # Desk job, no exercise
    "light": 1.375,  # Light exercise 1-3 days/week
    "moderate": 1.55,  # Moderate exercise 3-5 days/week
    "active": 1.725,  # Hard exercise 6-7 days/week
    "very_active": 1.9,  # Athlete / physical labor
}

# Calorie adjustments based on health goal
GOAL_CALORIE_ADJUSTMENTS: dict[str, int] = {
    "lose_weight": -500,  # ~0.5 kg/week loss
    "maintain": 0,
    "gain_weight": 300,  # Lean bulk
    "build_muscle": 400,  # Muscle building surplus
}

# Macro percentage splits per goal (protein%, carbs%, fat%)
GOAL_MACRO_SPLITS: dict[str, tuple[float, float, float]] = {
    "lose_weight": (0.30, 0.35, 0.35),
    "maintain": (0.25, 0.50, 0.25),
    "gain_weight": (0.25, 0.50, 0.25),
    "build_muscle": (0.30, 0.45, 0.25),
}

# FDA 2020 Recommended Daily Values
DAILY_VALUES: dict[str, float] = {
    "vitamin_a_mcg": 900,
    "vitamin_b6_mg": 1.7,
    "vitamin_b12_mcg": 2.4,
    "vitamin_c_mg": 90,
    "vitamin_d_mcg": 20,
    "folate_mcg": 400,
    "vitamin_e_mg": 15,
    "vitamin_k_mcg": 120,
    "calcium_mg": 1300,
    "iron_mg": 18,
    "magnesium_mg": 420,
    "potassium_mg": 4700,
    "sodium_mg": 2300,
    "zinc_mg": 11,
}

# USDA FoodData Central nutrient IDs
USDA_NUTRIENT_IDS: dict[str, int] = {
    "calories": 1008,
    "protein": 1003,
    "fat": 1004,
    "carbs": 1005,
    "fiber": 1079,
    "sugar": 2000,
    "vitamin_a": 1106,  # mcg RAE
    "vitamin_c": 1162,  # mg
    "vitamin_d": 1114,  # mcg
    "vitamin_b6": 1175,  # mg
    "vitamin_b12": 1178,  # mcg
    "folate": 1177,  # mcg
    "vitamin_e": 1109,  # mg
    "vitamin_k": 1185,  # mcg
    "calcium": 1087,  # mg
    "iron": 1089,  # mg
    "magnesium": 1090,  # mg
    "potassium": 1092,  # mg
    "sodium": 1093,  # mg
    "zinc": 1095,  # mg
}

# Redis cache TTLs in seconds
REDIS_TTL_NUTRITION = 7 * 24 * 3600  # 7 days
REDIS_TTL_USDA_SEARCH = 24 * 3600  # 24 hours
REDIS_TTL_DAILY_SUMMARY = 3600  # 1 hour
REDIS_TTL_RATE_LIMIT = 60  # 60 seconds

# Image constraints
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_DIMENSION_PX = 1536
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
