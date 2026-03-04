"""
Recommendation engine: generates personalized dietary advice based on
intake vs targets and micronutrient gaps.
"""


NUTRIENT_SUGGESTIONS: dict[str, str] = {
    "Iron": "Try spinach, lentils, or red meat.",
    "Calcium": "Add milk, curd, paneer, or ragi.",
    "Vitamin C": "Eat citrus fruits, amla, or bell peppers.",
    "Vitamin D": "Get some sunlight. Consider fortified foods.",
    "Vitamin B12": "Try dairy, eggs, or fortified cereals.",
    "Zinc": "Include nuts, seeds, chickpeas, or meat.",
    "Magnesium": "Add dark chocolate, bananas, or leafy greens.",
    "Potassium": "Try bananas, sweet potatoes, or coconut water.",
    "Folate": "Eat leafy greens, lentils, or fortified cereals.",
    "Vitamin A": "Add carrots, sweet potatoes, or spinach.",
    "Vitamin B6": "Try chickpeas, bananas, or poultry.",
}


def generate_recommendations(
    calories_consumed: float,
    protein_consumed: float,
    calorie_target: int,
    protein_target: int,
    low_nutrients: list[str],
) -> list[str]:
    """
    Generate smart dietary recommendations based on today's intake vs targets.

    Args:
        calories_consumed: Total calories consumed today.
        protein_consumed: Total protein consumed today (grams).
        calorie_target: Daily calorie target from profile.
        protein_target: Daily protein target from profile (grams).
        low_nutrients: List of nutrient names below 50% of daily value.

    Returns:
        List of actionable recommendation strings.
    """
    recommendations: list[str] = []
    cal_delta = calories_consumed - calorie_target

    # Calorie recommendations
    if cal_delta < -500:
        recommendations.append(
            f"You're {abs(round(cal_delta))} cal under your target. "
            "Consider a nutritious snack like nuts, yogurt, or a banana."
        )
    elif cal_delta < -200:
        recommendations.append(
            f"You're {abs(round(cal_delta))} cal under target. "
            "A light snack could help you meet your daily goal."
        )
    elif cal_delta > 300:
        recommendations.append(
            f"You've exceeded your calorie target by {round(cal_delta)} cal. "
            "Consider a lighter next meal or some extra activity."
        )

    # Protein recommendation
    protein_delta = protein_consumed - protein_target
    if protein_delta < -20:
        recommendations.append(
            f"You need {abs(round(protein_delta))}g more protein today. "
            "Try paneer, dal, eggs, chicken, or Greek yogurt."
        )

    # Micronutrient recommendations
    for nutrient in low_nutrients:
        suggestion = NUTRIENT_SUGGESTIONS.get(nutrient)
        if suggestion:
            recommendations.append(f"{nutrient} is low today. {suggestion}")

    if not recommendations:
        recommendations.append("Great job! You're on track with your nutrition goals today.")

    return recommendations
