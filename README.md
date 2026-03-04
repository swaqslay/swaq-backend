# Swaq — AI Food Photo Nutrition Analyzer

> **"Snap. Swaq. Slay."**

AI-powered food nutrition tracking app that analyzes meal photos to calculate calories, vitamins, and minerals with BMI-based personalized recommendations.

## Tech Stack

| Layer | Technology | Cost |
|-------|-----------|------|
| Backend API | FastAPI (Python 3.11+) | Free |
| Food Recognition | Gemini Flash (primary) + OpenRouter free models (fallback) | Free |
| Nutrition Database | USDA FoodData Central API | Free |
| Database | PostgreSQL (Supabase free tier) | Free |
| Cache | Redis (Upstash free tier) | Free |
| Auth | Supabase Auth | Free |
| Image Storage | Cloudflare R2 / Supabase Storage | Free tier |
| Mobile App | Flutter (Dart) | Free |

## Quick Start

```bash
# 1. Clone & setup
cd swaq
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run the server
uvicorn app.main:app --reload --port 8000
```

## API Keys Required (All Free)

1. **Gemini API Key**: https://aistudio.google.com/apikey
2. **OpenRouter API Key**: https://openrouter.ai/keys
3. **USDA API Key**: https://fdc.nal.usda.gov/api-key-signup
4. **Supabase**: https://supabase.com (for DB + Auth)

## Project Structure

```
swaq/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── core/
│   │   ├── config.py         # Environment & settings
│   │   └── database.py       # DB connection
│   ├── models/
│   │   ├── user.py           # User/Profile models
│   │   ├── meal.py           # Meal log models
│   │   └── nutrition.py      # Nutrition data models
│   ├── api/
│   │   ├── auth.py           # Auth endpoints
│   │   ├── meals.py          # Meal scanning endpoints
│   │   ├── profile.py        # User profile endpoints
│   │   └── dashboard.py      # Dashboard/stats endpoints
│   ├── services/
│   │   ├── ai_food_recognizer.py   # Gemini + OpenRouter AI
│   │   ├── nutrition_lookup.py     # USDA + IFCT lookup
│   │   ├── bmi_calculator.py       # BMI & goal engine
│   │   └── image_handler.py        # Image upload/storage
│   └── utils/
│       └── prompts.py        # AI prompt templates
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

## Architecture Flow

```
User takes food photo
        │
        ▼
  Flutter App (Camera)
        │
        ▼
  FastAPI Backend (/api/meals/scan)
        │
        ├──► AI Food Recognition (Gemini Flash → OpenRouter fallback)
        │         │
        │         ▼
        │    Identified foods + portions
        │         │
        ├──► Nutrition Lookup (USDA FoodData Central)
        │         │
        │         ▼
        │    Calories, Macros, Vitamins, Minerals
        │         │
        ├──► BMI Goal Engine
        │         │
        │         ▼
        │    Personalized recommendations
        │
        ▼
  Response to App (full nutrition breakdown + suggestions)
```
