# Project Context — Swaq AI Backend

## Business Domain

Swaq is an AI-powered food nutrition tracking mobile app targeting Gen Z health-conscious users (18-28) in India. Core flows:

1. **Photo Scan Flow**: User photographs a meal -> AI identifies food items -> nutrition breakdown returned (calories, macros, vitamins, minerals)
2. **Dashboard Flow**: User views daily/weekly nutrition summary vs personalized targets
3. **Profile Flow**: User sets body profile (age, gender, height, weight, activity, goal) -> BMI/BMR/TDEE auto-calculated -> daily targets set

## Tagline

"Snap. Swaq. Slay."

## Key Differentiators

- **Micronutrient depth**: Full vitamin (A, B6, B12, C, D, Folate) and mineral (Iron, Calcium, Zinc, Magnesium, Potassium, Sodium) tracking — not just calories + macros
- **Indian cuisine expertise**: Accurate recognition of dal, roti, biryani, paneer, dosa, idli, sambar, etc.
- **BMI-smart goals**: Dynamic daily targets based on user body profile and health goal
- **Deficiency alerts**: Warns when users consistently miss vitamins/minerals

## Monetization (Freemium)

- **Free tier**: 3 photo scans/day, basic calorie + macro tracking, 7-day meal history
- **Premium (Rs 149/month or Rs 999/year)**: Unlimited scans, full vitamin + mineral tracking, meal suggestions, weekly reports, unlimited history

## Target Audience

- Gen Z health-conscious users (18-28) in India
- Gym-goers, fitness enthusiasts, diet-conscious individuals
- People with specific dietary goals (weight loss, muscle gain, maintenance)

## Health Disclaimer Requirement

All AI-generated nutrition data must be clearly marked as estimates. The app is NOT a substitute for professional medical or dietary advice. This disclaimer must appear in onboarding, settings, and Terms of Service.

## Domain Terminology

- **Meal**: A single eating event (breakfast, lunch, dinner, snack) containing one or more food items
- **Food Item**: An individual food identified by AI within a meal (e.g., "dal", "rice", "roti")
- **Scan**: The act of photographing a meal for AI analysis
- **Daily Target**: Personalized calorie/macro/micro goals based on user profile
- **TDEE**: Total Daily Energy Expenditure — the calorie target before goal adjustment
- **BMR**: Basal Metabolic Rate — calories burned at rest
- **DV%**: Daily Value percentage — how much of a nutrient's recommended daily intake a food provides
