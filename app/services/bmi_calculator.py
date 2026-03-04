"""
BMI, BMR, TDEE, and macro target calculations.
Pure functions — no side effects, no DB access.
"""

from app.utils.constants import ACTIVITY_MULTIPLIERS, GOAL_CALORIE_ADJUSTMENTS, GOAL_MACRO_SPLITS


def calculate_bmi(weight_kg: float, height_cm: float) -> tuple[float, str]:
    """
    Calculate BMI and return (bmi_value, category_label).

    Categories (WHO standard):
      < 18.5  → Underweight
      18.5–24.9 → Normal weight
      25.0–29.9 → Overweight
      ≥ 30.0  → Obese
    """
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m**2), 1)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal weight"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"

    return bmi, category


def calculate_bmr(age: int, gender: str, height_cm: float, weight_kg: float) -> float:
    """
    Calculate Basal Metabolic Rate using the Mifflin-St Jeor equation.
    Most accurate non-laboratory BMR estimation.

    Male:   BMR = 10w + 6.25h - 5a + 5
    Female: BMR = 10w + 6.25h - 5a - 161
    """
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return round(base + 5 if gender == "male" else base - 161, 1)


def calculate_daily_targets(
    age: int,
    gender: str,
    height_cm: float,
    weight_kg: float,
    activity_level: str,
    health_goal: str,
) -> dict:
    """
    Calculate complete daily nutrition targets.

    Returns:
        dict with keys:
          bmi, bmi_category, bmr, tdee,
          daily_calorie_target, daily_protein_target_g,
          daily_carb_target_g, daily_fat_target_g
    """
    bmi, bmi_category = calculate_bmi(weight_kg, height_cm)
    bmr = calculate_bmr(age, gender, height_cm, weight_kg)

    activity_mult = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    tdee = round(bmr * activity_mult)

    goal_adj = GOAL_CALORIE_ADJUSTMENTS.get(health_goal, 0)
    calorie_target = tdee + goal_adj

    protein_pct, carb_pct, fat_pct = GOAL_MACRO_SPLITS.get(health_goal, (0.25, 0.50, 0.25))

    return {
        "bmi": bmi,
        "bmi_category": bmi_category,
        "bmr": bmr,
        "tdee": tdee,
        "daily_calorie_target": calorie_target,
        "daily_protein_target_g": round((calorie_target * protein_pct) / 4),
        "daily_carb_target_g": round((calorie_target * carb_pct) / 4),
        "daily_fat_target_g": round((calorie_target * fat_pct) / 9),
    }
