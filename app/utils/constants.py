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

# Pre-computed quick snack shortcuts (no AI/USDA calls needed)
QUICK_SNACKS: dict[str, dict] = {
    "masala_chai": {
        "name": "Masala Chai",
        "emoji": "\U0001f375",
        "category": "beverages",
        "default_portion": "1 cup (200ml)",
        "estimated_weight_g": 200,
        "calories": 100,
        "protein_g": 3.0,
        "carbs_g": 12.0,
        "fat_g": 4.0,
        "fiber_g": 0.0,
        "vitamins": {},
        "minerals": {},
    },
    "black_coffee": {
        "name": "Black Coffee",
        "emoji": "\u2615",
        "category": "beverages",
        "default_portion": "1 cup (150ml)",
        "estimated_weight_g": 150,
        "calories": 5,
        "protein_g": 0.3,
        "carbs_g": 1.0,
        "fat_g": 0.0,
        "fiber_g": 0.0,
        "vitamins": {},
        "minerals": {},
    },
    "coffee_milk": {
        "name": "Coffee with Milk",
        "emoji": "\u2615",
        "category": "beverages",
        "default_portion": "1 cup (200ml)",
        "estimated_weight_g": 200,
        "calories": 80,
        "protein_g": 3.0,
        "carbs_g": 10.0,
        "fat_g": 3.0,
        "fiber_g": 0.0,
        "vitamins": {},
        "minerals": {},
    },
    "samosa": {
        "name": "Samosa",
        "emoji": "\U0001f95f",
        "category": "fried_snacks",
        "default_portion": "1 pc (100g)",
        "estimated_weight_g": 100,
        "calories": 260,
        "protein_g": 4.0,
        "carbs_g": 30.0,
        "fat_g": 14.0,
        "fiber_g": 2.0,
        "vitamins": {},
        "minerals": {},
    },
    "pakora": {
        "name": "Pakora/Bhajia",
        "emoji": "\U0001f35f",
        "category": "fried_snacks",
        "default_portion": "5 pcs (120g)",
        "estimated_weight_g": 120,
        "calories": 300,
        "protein_g": 5.0,
        "carbs_g": 25.0,
        "fat_g": 20.0,
        "fiber_g": 2.0,
        "vitamins": {},
        "minerals": {},
    },
    "vada_pav": {
        "name": "Vada Pav",
        "emoji": "\U0001f354",
        "category": "fried_snacks",
        "default_portion": "1 pc (150g)",
        "estimated_weight_g": 150,
        "calories": 290,
        "protein_g": 5.0,
        "carbs_g": 36.0,
        "fat_g": 14.0,
        "fiber_g": 2.0,
        "vitamins": {},
        "minerals": {},
    },
    "marie_biscuit": {
        "name": "Marie Biscuit",
        "emoji": "\U0001f36a",
        "category": "biscuits",
        "default_portion": "4 pcs (30g)",
        "estimated_weight_g": 30,
        "calories": 120,
        "protein_g": 2.0,
        "carbs_g": 20.0,
        "fat_g": 4.0,
        "fiber_g": 0.5,
        "vitamins": {},
        "minerals": {},
    },
    "parle_g": {
        "name": "Parle-G",
        "emoji": "\U0001f36a",
        "category": "biscuits",
        "default_portion": "4 pcs (28g)",
        "estimated_weight_g": 28,
        "calories": 130,
        "protein_g": 2.0,
        "carbs_g": 22.0,
        "fat_g": 4.0,
        "fiber_g": 0.3,
        "vitamins": {},
        "minerals": {},
    },
    "bread_butter": {
        "name": "Bread & Butter",
        "emoji": "\U0001f35e",
        "category": "quick_bites",
        "default_portion": "2 slices (80g)",
        "estimated_weight_g": 80,
        "calories": 220,
        "protein_g": 5.0,
        "carbs_g": 26.0,
        "fat_g": 11.0,
        "fiber_g": 1.5,
        "vitamins": {},
        "minerals": {},
    },
    "banana": {
        "name": "Banana",
        "emoji": "\U0001f34c",
        "category": "fruits",
        "default_portion": "1 medium (120g)",
        "estimated_weight_g": 120,
        "calories": 105,
        "protein_g": 1.3,
        "carbs_g": 27.0,
        "fat_g": 0.4,
        "fiber_g": 3.1,
        "vitamins": {},
        "minerals": {},
    },
    "apple": {
        "name": "Apple",
        "emoji": "\U0001f34e",
        "category": "fruits",
        "default_portion": "1 medium (180g)",
        "estimated_weight_g": 180,
        "calories": 95,
        "protein_g": 0.5,
        "carbs_g": 25.0,
        "fat_g": 0.3,
        "fiber_g": 4.4,
        "vitamins": {},
        "minerals": {},
    },
    "peanuts_roasted": {
        "name": "Roasted Peanuts",
        "emoji": "\U0001f95c",
        "category": "quick_bites",
        "default_portion": "1 handful (30g)",
        "estimated_weight_g": 30,
        "calories": 170,
        "protein_g": 7.0,
        "carbs_g": 6.0,
        "fat_g": 14.0,
        "fiber_g": 2.4,
        "vitamins": {},
        "minerals": {},
    },
    "muri_mixture": {
        "name": "Muri/Chivda Mixture",
        "emoji": "\U0001f37f",
        "category": "quick_bites",
        "default_portion": "1 bowl (50g)",
        "estimated_weight_g": 50,
        "calories": 180,
        "protein_g": 4.0,
        "carbs_g": 22.0,
        "fat_g": 9.0,
        "fiber_g": 1.5,
        "vitamins": {},
        "minerals": {},
    },
    "bread_omelette": {
        "name": "Bread Omelette",
        "emoji": "\U0001f373",
        "category": "quick_bites",
        "default_portion": "2 egg (200g)",
        "estimated_weight_g": 200,
        "calories": 350,
        "protein_g": 16.0,
        "carbs_g": 28.0,
        "fat_g": 18.0,
        "fiber_g": 1.5,
        "vitamins": {},
        "minerals": {},
    },
    "maggi_noodles": {
        "name": "Maggi Noodles",
        "emoji": "\U0001f35c",
        "category": "quick_bites",
        "default_portion": "1 pack (70g)",
        "estimated_weight_g": 70,
        "calories": 420,
        "protein_g": 9.0,
        "carbs_g": 56.0,
        "fat_g": 17.0,
        "fiber_g": 2.0,
        "vitamins": {},
        "minerals": {},
    },
}
