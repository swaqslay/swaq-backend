# CLAUDE.md — Swaq AI Backend

> **Single source of truth for building the Swaq AI production backend.**
> Read this ENTIRE file before writing any code. Every architectural decision is intentional.

---

## 1. PROJECT OVERVIEW

### What is Swaq?

Swaq is an AI-powered food nutrition tracking mobile app. Users photograph their meals, and AI instantly identifies every food item and returns a complete nutritional breakdown — calories, macros (protein/carbs/fat), vitamins (A, B6, B12, C, D, Folate), and minerals (Iron, Calcium, Zinc, Magnesium, Potassium, Sodium). The app provides BMI-aware personalized daily targets and smart dietary recommendations.

### Core Value Proposition

- **Photo-first**: Snap a meal photo → get full nutrition in 3 seconds
- **Micronutrient depth**: Not just calories — full vitamin & mineral tracking (competitors only do calories + macros)
- **Indian cuisine expertise**: Accurate recognition of dal, roti, biryani, paneer, dosa, idli, sambar, etc.
- **BMI-smart goals**: Dynamic daily targets based on user's body profile and health goal
- **Deficiency alerts**: Warns when users consistently miss vitamins/minerals

### Target Audience

- Gen Z health-conscious users (18-28) in India
- Gym-goers, fitness enthusiasts, diet-conscious individuals
- People with specific dietary goals (weight loss, muscle gain, maintenance)

### Taglines

- Primary: **"Snap. Swaq. Slay."**
- Alt: "Know your food. Own your Swaq."
- Alt: "Eat smart. Stay Swaq."

---

## 2. TECH STACK (EXACT VERSIONS)

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Runtime** | Python | 3.11+ | Backend language |
| **Framework** | FastAPI | 0.115+ | Async REST API |
| **Server** | Uvicorn | 0.34+ | ASGI server |
| **ORM** | SQLAlchemy | 2.0+ | Async database ORM |
| **Migrations** | Alembic | 1.14+ | Schema migrations |
| **Validation** | Pydantic | 2.10+ | Request/response models |
| **AI Primary** | Google Gemini | gemini-2.0-flash | Food recognition (FREE) |
| **AI Fallback** | OpenRouter | OpenAI-compatible | Free vision models fallback |
| **Nutrition DB** | USDA FoodData Central | v1 REST API | 380K+ foods, vitamins, minerals (FREE) |
| **Database** | PostgreSQL | 16+ | Primary data store (Supabase free tier) |
| **Cache** | Redis | 7+ | USDA response caching (Upstash free tier) |
| **Auth** | Supabase Auth | - | Email/Google/Apple sign-in (FREE) |
| **Image Storage** | Cloudflare R2 | - | Food photo storage (10GB FREE) |
| **HTTP Client** | httpx | 0.28+ | Async HTTP for external APIs |
| **Testing** | pytest + pytest-asyncio | 8.3+ | Async test framework |
| **Linting** | Ruff | latest | Fast Python linter + formatter |

### Why These Choices

- **FastAPI over Django/Flask**: Native async, auto-generated OpenAPI docs, Pydantic integration, ideal for ML team onboarding later
- **Gemini over GPT-4V**: Free tier with 15 RPM / 1000 RPD / 250K TPM — more than enough for MVP
- **OpenRouter fallback**: Uses OpenAI-compatible API, so the client code is identical. Free vision models include Qwen3-VL, Gemma 3, Nemotron Nano VL
- **PostgreSQL over MongoDB**: Structured nutrition data benefits from relational schemas. Supabase gives free hosted PostgreSQL
- **Cloudflare R2 over S3**: S3-compatible API, 10GB free, zero egress fees

---

## 3. PROJECT STRUCTURE

```
swaq-backend/
├── CLAUDE.md                           # THIS FILE - project bible
├── .env                                # Local environment variables (NEVER commit)
├── .env.example                        # Template for env vars
├── .gitignore
├── pyproject.toml                      # Project config + dependencies
├── alembic.ini                         # Alembic migration config
├── alembic/                            # Database migrations
│   ├── env.py
│   ├── versions/                       # Migration files
│   └── script.py.mako
│
├── app/                                # Application source code
│   ├── __init__.py
│   ├── main.py                         # FastAPI app factory + lifespan
│   │
│   ├── core/                           # Framework-level config
│   │   ├── __init__.py
│   │   ├── config.py                   # Pydantic Settings (env vars)
│   │   ├── database.py                 # Async engine + session factory
│   │   ├── redis.py                    # Redis connection pool
│   │   ├── security.py                 # JWT creation/verification, password hashing
│   │   └── exceptions.py              # Custom exception classes + handlers
│   │
│   ├── models/                         # SQLAlchemy ORM models (DB tables)
│   │   ├── __init__.py
│   │   ├── user.py                     # User + UserProfile tables
│   │   ├── meal.py                     # Meal + MealFoodItem tables
│   │   └── nutrition_cache.py          # Cached USDA lookups
│   │
│   ├── schemas/                        # Pydantic schemas (API request/response)
│   │   ├── __init__.py
│   │   ├── auth.py                     # Login, Register, Token schemas
│   │   ├── user.py                     # Profile create/update/response
│   │   ├── meal.py                     # Meal scan request/response
│   │   ├── nutrition.py                # Nutrition data structures
│   │   └── dashboard.py               # Daily/weekly summary schemas
│   │
│   ├── api/                            # Route handlers (thin controllers)
│   │   ├── __init__.py
│   │   ├── router.py                   # Main router aggregator
│   │   ├── v1/                         # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                 # POST /register, /login, /refresh
│   │   │   ├── meals.py                # POST /scan, GET /history, GET /{id}
│   │   │   ├── profile.py              # POST/GET/PATCH /profile
│   │   │   └── dashboard.py            # GET /today, /weekly, /trends
│   │   └── deps.py                     # Shared dependencies (get_current_user, get_db)
│   │
│   ├── services/                       # Business logic layer
│   │   ├── __init__.py
│   │   ├── ai_recognizer.py            # Gemini + OpenRouter food recognition
│   │   ├── nutrition_service.py        # USDA lookup + caching + AI estimation
│   │   ├── meal_service.py             # Meal CRUD + aggregation
│   │   ├── profile_service.py          # BMI/BMR/TDEE calculation + targets
│   │   ├── recommendation_engine.py    # Smart dietary recommendations
│   │   └── image_storage.py            # Cloudflare R2 upload/retrieval
│   │
│   └── utils/                          # Shared utilities
│       ├── __init__.py
│       ├── prompts.py                  # AI prompt templates
│       ├── constants.py                # RDA values, activity multipliers, etc.
│       └── helpers.py                  # Date parsing, UUID generation, etc.
│
├── tests/                              # Test suite
│   ├── __init__.py
│   ├── conftest.py                     # Shared fixtures (test DB, client, auth)
│   ├── test_auth.py
│   ├── test_meals.py
│   ├── test_profile.py
│   ├── test_nutrition.py
│   ├── test_ai_recognizer.py
│   └── test_recommendations.py
│
├── scripts/                            # Utility scripts
│   ├── seed_indian_foods.py            # Seed IFCT 2017 data into DB
│   ├── test_gemini.py                  # Quick Gemini API test
│   └── test_openrouter.py             # Quick OpenRouter API test
│
└── docker/                             # Deployment
    ├── Dockerfile
    ├── docker-compose.yml              # Local dev (app + postgres + redis)
    └── docker-compose.prod.yml         # Production config
```

### CRITICAL RULES

- **NEVER put business logic in route handlers (api/)**. Route handlers are THIN — they validate input, call a service, return the response. All logic lives in `services/`.
- **NEVER import from `api/` in `services/`**. Dependencies flow ONE direction: `api/ → services/ → models/`.
- **NEVER access `request` object in services**. Pass only the data the service needs.
- **ALL database queries go through services**, not directly in route handlers.
- **ALL external API calls go through services** with proper error handling and fallback.

---

## 4. DATABASE SCHEMA

Use SQLAlchemy 2.0 async ORM with Mapped types. All timestamps are UTC. All UUIDs use `uuid7()` for sortability.

### Table: `users`

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_premium: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(back_populates="user", uselist=False)
    meals: Mapped[list["Meal"]] = relationship(back_populates="user", order_by="Meal.created_at.desc()")
```

### Table: `user_profiles`

```python
class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    age: Mapped[int] = mapped_column(nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)  # male, female, other
    height_cm: Mapped[float] = mapped_column(nullable=False)
    weight_kg: Mapped[float] = mapped_column(nullable=False)
    activity_level: Mapped[str] = mapped_column(String(20), default="moderate")
    health_goal: Mapped[str] = mapped_column(String(20), default="maintain")
    dietary_restrictions: Mapped[list] = mapped_column(JSON, default=list)

    # Computed targets (recalculated on profile update)
    bmi: Mapped[float] = mapped_column(nullable=False)
    daily_calorie_target: Mapped[int] = mapped_column(nullable=False)
    daily_protein_target_g: Mapped[int] = mapped_column(nullable=False)
    daily_carb_target_g: Mapped[int] = mapped_column(nullable=False)
    daily_fat_target_g: Mapped[int] = mapped_column(nullable=False)

    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")
```

### Table: `meals`

```python
class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # breakfast, lunch, dinner, snack
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Aggregated totals (denormalized for fast dashboard queries)
    total_calories: Mapped[float] = mapped_column(default=0)
    total_protein_g: Mapped[float] = mapped_column(default=0)
    total_carbs_g: Mapped[float] = mapped_column(default=0)
    total_fat_g: Mapped[float] = mapped_column(default=0)
    total_fiber_g: Mapped[float] = mapped_column(default=0)

    # AI metadata
    ai_provider: Mapped[str] = mapped_column(String(20))   # gemini, openrouter
    ai_model: Mapped[str] = mapped_column(String(100))
    ai_confidence_avg: Mapped[float] = mapped_column(default=0)

    # Manual correction flag
    is_manually_edited: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(default=func.now(), index=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="meals")
    food_items: Mapped[list["MealFoodItem"]] = relationship(back_populates="meal", cascade="all, delete-orphan")
```

### Table: `meal_food_items`

```python
class MealFoodItem(Base):
    __tablename__ = "meal_food_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    meal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)

    # Identification
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence: Mapped[float] = mapped_column(default=0.8)
    estimated_portion: Mapped[str] = mapped_column(String(100))
    estimated_weight_g: Mapped[float] = mapped_column(nullable=False)

    # Macros
    calories: Mapped[float] = mapped_column(default=0)
    protein_g: Mapped[float] = mapped_column(default=0)
    carbs_g: Mapped[float] = mapped_column(default=0)
    fat_g: Mapped[float] = mapped_column(default=0)
    fiber_g: Mapped[float] = mapped_column(default=0)

    # Micronutrients stored as JSON for flexibility
    vitamins: Mapped[dict] = mapped_column(JSON, default=dict)
    # Structure: {"vitamin_c": {"amount": 15.2, "unit": "mg", "dv_percent": 16.9}, ...}
    minerals: Mapped[dict] = mapped_column(JSON, default=dict)
    # Structure: {"iron": {"amount": 2.1, "unit": "mg", "dv_percent": 11.7}, ...}

    # USDA reference (if matched)
    usda_fdc_id: Mapped[Optional[int]] = mapped_column()

    # Relationships
    meal: Mapped["Meal"] = relationship(back_populates="food_items")
```

### Table: `nutrition_cache`

```python
class NutritionCache(Base):
    """Cache USDA lookups to reduce API calls. TTL managed by Redis."""
    __tablename__ = "nutrition_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    food_name_normalized: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    usda_fdc_id: Mapped[Optional[int]] = mapped_column()
    nutrition_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(20))  # usda, ifct, ai_estimated
    created_at: Mapped[datetime] = mapped_column(default=func.now())
```

### Indexes

```sql
-- Fast dashboard queries: "get all meals for user X on date Y"
CREATE INDEX idx_meals_user_date ON meals (user_id, created_at DESC);

-- Fast nutrition cache lookups
CREATE INDEX idx_nutrition_cache_name ON nutrition_cache (food_name_normalized);
```

---

## 5. API SPECIFICATION

All endpoints are prefixed with `/api/v1/`. All responses use standard envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

Error responses:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": { ... }
  }
}
```

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | None | Create account (email, name, password) |
| POST | `/auth/login` | None | Login → returns access_token + refresh_token |
| POST | `/auth/refresh` | Refresh Token | Get new access_token |
| POST | `/auth/google` | None | Google OAuth sign-in |

**Token strategy**: Short-lived access tokens (15 min) + long-lived refresh tokens (30 days). Access token in `Authorization: Bearer <token>` header.

### Profile

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/profile` | Required | Create profile (age, gender, height, weight, goal) → auto-calculates BMI + daily targets |
| GET | `/profile` | Required | Get current profile with targets |
| PATCH | `/profile` | Required | Update profile fields → recalculates targets |

### Meals (CORE)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/meals/scan` | Required | **Upload food photo** → AI recognition → nutrition analysis → save + return full breakdown |
| GET | `/meals/history` | Required | Get meal history (query: `?date=2025-03-15` or `?from=&to=`) |
| GET | `/meals/{meal_id}` | Required | Get single meal with all food items + nutrition |
| PATCH | `/meals/{meal_id}/items/{item_id}` | Required | Manual correction (change food name, portion, calories) |
| DELETE | `/meals/{meal_id}` | Required | Delete a meal |

### Dashboard

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/dashboard/today` | Required | Today's consumed vs targets + recommendations |
| GET | `/dashboard/weekly` | Required | 7-day averages, trends, consistently low nutrients |
| GET | `/dashboard/nutrients` | Required | Micronutrient heatmap (last 7 days) |

### System

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Service health + API key status |
| GET | `/health/ready` | None | Full readiness check (DB + Redis + AI) |

---

## 6. AI FOOD RECOGNITION — IMPLEMENTATION DETAILS

### Architecture: Two-Step Pipeline

The food recognition is split into TWO separate AI calls for reliability:

**Step 1 — Visual Identification** (requires vision model):
- Input: Food photo (JPEG/PNG/WebP, max 10MB)
- Output: List of food items + estimated portions + confidence scores
- Model: Gemini 2.0 Flash Vision (primary) → OpenRouter free vision (fallback)

**Step 2 — Nutrition Estimation** (text-only, cheaper):
- Input: List of identified food items with portions from Step 1
- Output: Complete nutritional profile per item (calories, macros, vitamins, minerals)
- Model: Gemini 2.0 Flash text (primary) → OpenRouter free text (fallback)
- Enhanced by: USDA FoodData Central lookup for known foods

### Provider Configuration

```python
# Primary: Gemini Flash (FREE tier limits)
GEMINI_CONFIG = {
    "model": "gemini-2.0-flash",
    "api_base": "https://generativelanguage.googleapis.com/v1beta",
    "free_tier_limits": {
        "requests_per_minute": 15,
        "requests_per_day": 1000,       # Plenty for MVP (1000 scans/day)
        "tokens_per_minute": 250_000,
    },
    "temperature": 0.15,               # Low for consistent structured output
    "max_output_tokens": 4096,
    "response_mime_type": "application/json",  # Force JSON mode
}

# Fallback: OpenRouter Free Vision Models (tried in order)
OPENROUTER_CONFIG = {
    "api_base": "https://openrouter.ai/api/v1",
    "vision_models": [
        "qwen/qwen3-vl-30b-a3b:free",          # Best free vision model
        "google/gemma-3-27b-it:free",            # Google's open model
        "nvidia/nemotron-nano-2-vl:free",        # NVIDIA vision
        "openrouter/free",                        # Auto-select any available free model
    ],
    "text_models": [
        "qwen/qwen3-235b-a22b:free",            # Best free text model
        "google/gemma-3-27b-it:free",
        "openrouter/free",
    ],
    "temperature": 0.15,
    "max_tokens": 4096,
}
```

### Failover Logic

```
Request comes in
    │
    ├─► Try Gemini Flash
    │     ├─ Success → return result
    │     └─ Fail (429/500/timeout) → log warning
    │
    ├─► Try OpenRouter model 1 (Qwen3-VL)
    │     ├─ Success → return result
    │     └─ Fail → try next
    │
    ├─► Try OpenRouter model 2 (Gemma 3)
    │     ├─ Success → return result
    │     └─ Fail → try next
    │
    ├─► Try OpenRouter model 3 (Nemotron)
    │     ├─ Success → return result
    │     └─ Fail → try next
    │
    ├─► Try OpenRouter auto-router (openrouter/free)
    │     ├─ Success → return result
    │     └─ Fail → all providers exhausted
    │
    └─► Raise ServiceUnavailableError
          "All AI providers are temporarily unavailable. Please try again in a moment."
```

### Prompt Engineering

The prompts are in `app/utils/prompts.py`. They MUST:

1. **Start with a system role** defining the AI as an expert food nutritionist
2. **Demand JSON-only output** — no markdown, no explanation, no backticks
3. **Specify exact JSON schema** the response must follow
4. **Include Indian food examples** so the model recognizes desi cuisine
5. **Use low temperature (0.15)** for consistent structured output
6. **Use Gemini's `responseMimeType: "application/json"`** to force JSON mode

### Image Preprocessing

Before sending to AI:
1. Validate: JPEG, PNG, or WebP only. Max 10MB.
2. Resize: If image > 1536px on longest edge, resize to 1536px (saves tokens, no quality loss for food recognition)
3. Convert: Always send as base64 with correct MIME type
4. EXIF: Strip EXIF data for privacy (no GPS coordinates)

---

## 7. NUTRITION DATABASE STRATEGY

### Three-Tier Lookup

For each identified food item, nutrition data is resolved in this order:

**Tier 1: Redis Cache** (fastest, ~1ms)
- Key: `nutrition:{normalized_food_name}`
- TTL: 7 days
- Hit rate: ~70% after warm-up (most users eat similar foods)

**Tier 2: PostgreSQL nutrition_cache table** (fast, ~5ms)
- Contains previously resolved nutrition data
- Both USDA results and AI-estimated results
- Permanent storage (Redis is just the hot layer)

**Tier 3: External Lookup** (slow, ~200-500ms)
```
Food identified by AI
    │
    ├─► Search USDA FoodData Central API
    │     ├─ Found → use USDA data (most authoritative)
    │     └─ Not found (common for Indian foods)
    │           │
    │           ├─► Check Indian Food Composition Tables (local DB)
    │           │     ├─ Found → use IFCT data
    │           │     └─ Not found
    │           │           │
    │           └───────────► Use AI estimation from Step 2
    │                          (already calculated, use as final fallback)
    │
    └─► Cache result in Redis + PostgreSQL
```

### USDA FoodData Central API

```
Base URL: https://api.nal.usda.gov/fdc/v1
Rate Limit: 1,000 requests/hour (per API key)
Data Types to search: "Foundation" and "SR Legacy" (most accurate)

Key Nutrient IDs:
  Calories       = 1008
  Protein        = 1003
  Total Fat      = 1004
  Carbohydrates  = 1005
  Fiber          = 1079
  Vitamin A      = 1106 (mcg RAE)
  Vitamin B6     = 1175 (mg)
  Vitamin B12    = 1178 (mcg)
  Vitamin C      = 1162 (mg)
  Vitamin D      = 1114 (mcg)
  Folate         = 1177 (mcg)
  Calcium        = 1087 (mg)
  Iron           = 1089 (mg)
  Magnesium      = 1090 (mg)
  Potassium      = 1092 (mg)
  Sodium         = 1093 (mg)
  Zinc           = 1095 (mg)
```

### Recommended Daily Values (FDA 2020)

```python
DAILY_VALUES = {
    "vitamin_a_mcg": 900,
    "vitamin_b6_mg": 1.7,
    "vitamin_b12_mcg": 2.4,
    "vitamin_c_mg": 90,
    "vitamin_d_mcg": 20,
    "folate_mcg": 400,
    "calcium_mg": 1300,
    "iron_mg": 18,
    "magnesium_mg": 420,
    "potassium_mg": 4700,
    "sodium_mg": 2300,
    "zinc_mg": 11,
}
```

---

## 8. AUTHENTICATION & SECURITY

### Auth Flow

```
Register:
  POST /auth/register {email, name, password}
  → Hash password with bcrypt (12 rounds)
  → Create user in DB
  → Return access_token (JWT, 15 min) + refresh_token (JWT, 30 days)

Login:
  POST /auth/login {email, password}
  → Verify bcrypt hash
  → Return access_token + refresh_token

Refresh:
  POST /auth/refresh {refresh_token}
  → Verify refresh token signature + expiry
  → Return new access_token

Protected Endpoints:
  Header: Authorization: Bearer <access_token>
  → Decode JWT → extract user_id → fetch user from DB → inject as dependency
```

### JWT Configuration

```python
JWT_CONFIG = {
    "algorithm": "HS256",
    "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 30,
    "issuer": "swaq-api",
}
```

### Password Rules

- Minimum 8 characters
- Hashed with bcrypt, 12 salt rounds
- NEVER stored in plaintext, NEVER logged, NEVER returned in API responses

### Security Headers (Middleware)

```python
# Add to all responses
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### Rate Limiting

```python
# Apply per-endpoint rate limits
RATE_LIMITS = {
    "/auth/register": "5/minute",       # Prevent spam registrations
    "/auth/login": "10/minute",          # Prevent brute force
    "/meals/scan": "30/minute",          # AI cost protection
    "default": "100/minute",             # General endpoints
}
```

### CORS Configuration

```python
CORS_CONFIG = {
    "allow_origins": [
        "http://localhost:3000",          # Local Flutter web dev
        "http://localhost:8080",          # Local dev
        "https://swaq.app",           # Production web (preferred)
        # Alt domains: getswaq.com, swaq.io, swaqapp.com
    ],
    "allow_methods": ["GET", "POST", "PATCH", "DELETE"],
    "allow_headers": ["Authorization", "Content-Type"],
    "allow_credentials": True,
}
```

---

## 9. ERROR HANDLING

### Custom Exception Hierarchy

```python
class SwaqError(Exception):
    """Base exception. All custom errors extend this."""
    def __init__(self, message: str, code: str, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code

class ValidationError(SwaqError):       # 400
class AuthenticationError(SwaqError):    # 401
class ForbiddenError(SwaqError):         # 403
class NotFoundError(SwaqError):          # 404
class RateLimitError(SwaqError):         # 429
class AIProviderError(SwaqError):        # 502
class ServiceUnavailableError(SwaqError): # 503
```

### Error Codes (used in API responses)

```
AUTH_INVALID_CREDENTIALS     - Wrong email or password
AUTH_TOKEN_EXPIRED           - Access token expired, use refresh
AUTH_TOKEN_INVALID           - Malformed or tampered token
AUTH_EMAIL_EXISTS             - Email already registered

PROFILE_NOT_FOUND            - User hasn't created profile yet
PROFILE_INVALID_DATA         - Validation error on profile fields

MEAL_NOT_FOUND               - Meal ID doesn't exist or belongs to another user
MEAL_SCAN_FAILED             - AI couldn't identify any food in the image
MEAL_IMAGE_INVALID           - Unsupported format or too large
MEAL_IMAGE_TOO_LARGE         - Image exceeds 10MB limit

AI_ALL_PROVIDERS_FAILED      - Both Gemini and OpenRouter failed
AI_INVALID_RESPONSE          - AI returned unparseable response

NUTRITION_LOOKUP_FAILED      - USDA API failed and no cached data

RATE_LIMIT_EXCEEDED          - Too many requests
INTERNAL_ERROR               - Unexpected server error
```

### Global Exception Handler

Register in `app/main.py`:

```python
@app.exception_handler(SwaqError)
async def swaq_error_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        }
    )
```

---

## 10. BMI & RECOMMENDATION ENGINE

### BMI Calculation

```
BMI = weight_kg / (height_m ^ 2)

Categories:
  < 18.5  → Underweight
  18.5-24.9 → Normal weight
  25.0-29.9 → Overweight
  ≥ 30.0  → Obese
```

### BMR (Basal Metabolic Rate) — Mifflin-St Jeor

```
Male:   BMR = 10 × weight_kg + 6.25 × height_cm - 5 × age + 5
Female: BMR = 10 × weight_kg + 6.25 × height_cm - 5 × age - 161
```

### TDEE (Total Daily Energy Expenditure)

```
TDEE = BMR × Activity Multiplier

Multipliers:
  sedentary   = 1.2    (desk job, no exercise)
  light       = 1.375  (light exercise 1-3 days/week)
  moderate    = 1.55   (moderate exercise 3-5 days/week)
  active      = 1.725  (hard exercise 6-7 days/week)
  very_active = 1.9    (athlete / physical labor)
```

### Goal-Based Calorie Adjustment

```
lose_weight   = TDEE - 500    (~0.5 kg/week loss)
maintain      = TDEE
gain_weight   = TDEE + 300    (lean bulk)
build_muscle  = TDEE + 400    (muscle building surplus)
```

### Macro Split

```
                   Protein   Carbs   Fat
lose_weight:       30%       35%     35%
maintain:          25%       50%     25%
gain_weight:       25%       50%     25%
build_muscle:      30%       45%     25%

Conversion: protein/carbs = 4 cal/g, fat = 9 cal/g
```

### Recommendation Engine Logic

After each meal scan, compare today's cumulative intake against targets:

```python
def generate_recommendations(consumed, targets, low_nutrients):
    recs = []

    cal_delta = consumed.calories - targets.calories
    if cal_delta < -500:
        recs.append("You're {abs(cal_delta)} cal under target. Add a protein-rich snack.")
    elif cal_delta > 300:
        recs.append("You've exceeded your target by {cal_delta} cal. Consider lighter next meal.")

    if consumed.protein < targets.protein - 20:
        recs.append("Need {gap}g more protein. Try paneer, dal, eggs, or chicken.")

    # Micronutrient alerts
    nutrient_suggestions = {
        "Iron": "Try spinach, lentils, or red meat.",
        "Calcium": "Add milk, curd, paneer, or ragi.",
        "Vitamin C": "Eat citrus fruits, amla, or bell peppers.",
        "Vitamin D": "Get some sunlight. Consider fortified foods.",
        "Vitamin B12": "Try dairy, eggs, or fortified cereals.",
        "Zinc": "Include nuts, seeds, chickpeas, or meat.",
        "Magnesium": "Add dark chocolate, bananas, or leafy greens.",
    }

    for nutrient in low_nutrients:
        if nutrient in nutrient_suggestions:
            recs.append(f"{nutrient} is low today. {nutrient_suggestions[nutrient]}")

    if not recs:
        recs.append("Great job! You're on track with your nutrition today.")

    return recs
```

---

## 11. IMAGE HANDLING

### Upload Flow

```
1. User sends photo via multipart/form-data
2. Server validates: JPEG/PNG/WebP, max 10MB
3. Strip EXIF metadata (privacy)
4. Resize if longest edge > 1536px
5. Generate unique filename: {user_id}/{uuid7}.{ext}
6. Upload to Cloudflare R2
7. Store R2 URL in meal record
8. Send original (or resized) bytes to AI for recognition
```

### Cloudflare R2 Integration

```python
# S3-compatible API — use boto3
import boto3

r2_client = boto3.client(
    "s3",
    endpoint_url=settings.cloudflare_r2_endpoint,
    aws_access_key_id=settings.cloudflare_r2_access_key,
    aws_secret_access_key=settings.cloudflare_r2_secret_key,
    region_name="auto",
)

# Upload
r2_client.put_object(
    Bucket=settings.cloudflare_r2_bucket,
    Key=f"{user_id}/{filename}",
    Body=image_bytes,
    ContentType=mime_type,
)

# Generate signed URL (for Flutter app to display)
url = r2_client.generate_presigned_url(
    "get_object",
    Params={"Bucket": bucket, "Key": key},
    ExpiresIn=3600,  # 1 hour
)
```

---

## 12. CACHING STRATEGY

### Redis Keys

```
nutrition:{normalized_name}     → JSON nutrition data      TTL: 7 days
usda_search:{query_hash}        → JSON search results      TTL: 24 hours
user_daily:{user_id}:{date}     → JSON daily summary       TTL: 1 hour
rate_limit:{endpoint}:{ip}      → request count            TTL: 60 seconds
```

### Cache-Through Pattern

```python
async def get_nutrition(food_name: str) -> dict:
    # Normalize: lowercase, strip whitespace, remove special chars
    key = f"nutrition:{normalize(food_name)}"

    # 1. Try Redis
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)

    # 2. Try PostgreSQL cache
    db_cached = await db.query(NutritionCache).filter_by(food_name_normalized=normalize(food_name)).first()
    if db_cached:
        await redis.set(key, json.dumps(db_cached.nutrition_data), ex=7*86400)
        return db_cached.nutrition_data

    # 3. Fetch from USDA / AI
    data = await fetch_from_usda_or_ai(food_name)

    # 4. Store in both caches
    await redis.set(key, json.dumps(data), ex=7*86400)
    db.add(NutritionCache(food_name_normalized=normalize(food_name), nutrition_data=data, source="usda"))
    await db.commit()

    return data
```

---

## 13. TESTING STRATEGY

### Test Configuration

```python
# tests/conftest.py

@pytest.fixture
async def test_db():
    """Create fresh SQLite test database for each test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine)() as session:
        yield session

@pytest.fixture
async def test_client(test_db):
    """FastAPI test client with overridden DB dependency."""
    app.dependency_overrides[get_db] = lambda: test_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def auth_headers(test_client):
    """Pre-authenticated headers for protected endpoints."""
    # Register + login → return {"Authorization": "Bearer <token>"}
```

### What to Test

```
Unit Tests (services/):
  ✓ BMI calculation edge cases (very short, very tall, underweight, obese)
  ✓ BMR calculation for male/female
  ✓ TDEE with all activity levels
  ✓ Macro split calculation
  ✓ Recommendation engine with various nutrient gaps
  ✓ AI response JSON parsing (valid, malformed, empty)
  ✓ USDA nutrient scaling (per 100g → actual portion)
  ✓ Food name normalization

Integration Tests (api/):
  ✓ Register → login → get token → access protected endpoint
  ✓ Create profile → verify BMI and targets calculated
  ✓ Upload food photo → get meal analysis (mock AI response)
  ✓ Get daily dashboard → verify aggregation
  ✓ Manual meal correction → verify totals recalculated
  ✓ Rate limiting works correctly
  ✓ Invalid token → 401

AI Service Tests (mock external APIs):
  ✓ Gemini success → returns structured result
  ✓ Gemini fails → falls back to OpenRouter
  ✓ Both fail → returns ServiceUnavailableError
  ✓ AI returns invalid JSON → graceful error
  ✓ AI returns empty food list → MEAL_SCAN_FAILED
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_meals.py -v

# Run only unit tests
pytest tests/ -v -k "not integration"
```

---

## 14. DEPLOYMENT

### Local Development

```bash
# 1. Clone repo
git clone <repo-url> && cd swaq-backend

# 2. Setup Python env
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# 3. Configure
cp .env.example .env
# Edit .env with your API keys

# 4. Start dependencies (if using Docker)
docker compose up -d postgres redis

# 5. Run migrations
alembic upgrade head

# 6. Start server
uvicorn app.main:app --reload --port 8000

# 7. Open docs
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml (local dev)
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis]
    volumes: ["./app:/app/app"]  # Hot reload

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: swaq
      POSTGRES_USER: swaq
      POSTGRES_PASSWORD: localdev
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

### Production Deployment (Railway / Render)

```
1. Push code to GitHub
2. Connect GitHub repo to Railway.app (or Render.com)
3. Set environment variables in Railway dashboard
4. Railway auto-detects Python → builds → deploys
5. Add PostgreSQL addon (free tier: 500MB)
6. Add Redis addon (or use Upstash free tier)
7. Set custom domain: api.swaq.app
```

### Environment Variables for Production

```
APP_ENV=production
SECRET_KEY=<generate-with: openssl rand -hex 32>
DATABASE_URL=<railway-provides-this>
REDIS_URL=<railway-or-upstash-provides>
GEMINI_API_KEY=<your-key>
OPENROUTER_API_KEY=<your-key>
USDA_API_KEY=<your-key>
CLOUDFLARE_R2_ENDPOINT=<your-endpoint>
CLOUDFLARE_R2_ACCESS_KEY=<your-key>
CLOUDFLARE_R2_SECRET_KEY=<your-key>
CORS_ORIGINS=https://swaq.app
```

---

## 15. CODING STANDARDS

### Python Style

- **Formatter**: Ruff (use `ruff format`)
- **Linter**: Ruff (use `ruff check`)
- **Line length**: 100 characters max
- **Quotes**: Double quotes for strings
- **Imports**: Absolute imports only. Group: stdlib → third-party → local. Sorted alphabetically within groups.
- **Type hints**: Required on ALL function signatures. Use `Mapped[]` for SQLAlchemy models.
- **Docstrings**: Required on all public functions, classes, and modules. Google style.

### Naming Conventions

```
Files:              snake_case.py
Classes:            PascalCase
Functions/methods:  snake_case
Variables:          snake_case
Constants:          UPPER_SNAKE_CASE
Pydantic schemas:   PascalCase (UserCreate, MealResponse)
SQLAlchemy models:  PascalCase singular (User, Meal, MealFoodItem)
DB tables:          snake_case plural (users, meals, meal_food_items)
API endpoints:      kebab-case (/api/v1/meals/scan)
Env variables:      UPPER_SNAKE_CASE
```

### Async Rules

- **ALL database operations must be async** (use `async def` + `await`)
- **ALL external HTTP calls must be async** (use `httpx.AsyncClient`)
- **NEVER use `time.sleep()`** — use `asyncio.sleep()` if needed
- **NEVER use synchronous `requests` library** — always `httpx`

### Git Conventions

```
Branch naming:
  feature/meal-scanning
  fix/gemini-timeout
  refactor/nutrition-cache

Commit messages (conventional commits):
  feat: add meal photo scanning endpoint
  fix: handle Gemini rate limit 429 response
  refactor: extract nutrition cache into service
  test: add BMI calculation edge cases
  docs: update API documentation
  chore: update dependencies
```

---

## 16. ENVIRONMENT SETUP

### Required API Keys (ALL FREE)

1. **Gemini API Key**
   - Go to: https://aistudio.google.com/apikey
   - Click "Create API Key"
   - Copy to `.env` as `GEMINI_API_KEY`

2. **OpenRouter API Key**
   - Go to: https://openrouter.ai/keys
   - Sign up / login
   - Create new key
   - Copy to `.env` as `OPENROUTER_API_KEY`

3. **USDA FoodData Central API Key**
   - Go to: https://fdc.nal.usda.gov/api-key-signup
   - Fill form → key sent to email
   - Copy to `.env` as `USDA_API_KEY`

4. **Supabase** (Database + Auth)
   - Go to: https://supabase.com
   - Create project
   - Copy DB URL, Anon Key, and Project URL to `.env`

5. **Cloudflare R2** (Image Storage)
   - Go to: https://dash.cloudflare.com → R2
   - Create bucket named `swaq-images`
   - Create API token with R2 read/write
   - Copy endpoint, access key, secret key to `.env`

6. **Upstash Redis** (Optional, for cache)
   - Go to: https://upstash.com
   - Create Redis database (free tier)
   - Copy `REDIS_URL` to `.env`

---

## 17. HEALTH DISCLAIMER (MUST INCLUDE)

The app MUST display these disclaimers prominently:

- In onboarding flow (before first use)
- In app settings
- In Terms of Service

```
"Swaq provides estimated nutritional information based on AI analysis
and public nutrition databases. It is NOT a substitute for professional
medical or dietary advice.

- Nutritional estimates may contain errors due to AI recognition limitations
- Portion size estimation is approximate
- Consult a healthcare professional before making dietary changes
- This app is not intended to diagnose, treat, or prevent any disease"
```

---

## 18. WHAT TO BUILD FIRST (PRIORITY ORDER)

Build in this EXACT order. Each step should be fully working before moving to the next.

```
Week 1: Foundation
  ├── [1] Project scaffolding (pyproject.toml, directory structure, configs)
  ├── [2] Database models + Alembic migrations
  ├── [3] Auth endpoints (register, login, refresh, JWT)
  └── [4] Profile endpoints (create, get, update with BMI calculation)

Week 2: Core AI Pipeline
  ├── [5] AI food recognizer service (Gemini + OpenRouter fallback)
  ├── [6] AI prompt templates + JSON parsing
  ├── [7] POST /meals/scan endpoint (upload photo → AI → return nutrition)
  └── [8] Manual correction endpoint (PATCH food items)

Week 3: Nutrition & Dashboard
  ├── [9] USDA nutrition lookup service + caching
  ├── [10] Meal history endpoint + daily aggregation
  ├── [11] Dashboard today + weekly endpoints
  └── [12] Recommendation engine

Week 4: Production Hardening
  ├── [13] Image storage (Cloudflare R2 upload)
  ├── [14] Rate limiting middleware
  ├── [15] Error handling + logging
  ├── [16] Tests (unit + integration)
  ├── [17] Docker setup
  └── [18] Deploy to Railway
```

---

## 19. SCALING ROADMAP

```
Phase 1 (0-500 users):
  - Gemini free tier handles all scans
  - Single Railway instance
  - Cost: ₹0/month

Phase 2 (500-5K users):
  - May hit Gemini rate limits at peak → OpenRouter absorbs overflow
  - Add Redis cache to reduce USDA calls
  - Cost: ₹0/month (still free tiers)

Phase 3 (5K-25K users):
  - Revenue from premium subscribers covers costs
  - Upgrade to Supabase Pro ($25/month)
  - Add Gemini paid tier ($0.01 per 1M tokens)
  - Cost: ~₹3,000-5,000/month

Phase 4 (25K+ users):
  - Train custom food recognition model on user-uploaded images
  - Move to dedicated GPU server for AI inference
  - Multi-region deployment
  - Cost: ₹15,000-50,000/month (covered by revenue)
```

---

## 20. KEY BUSINESS CONTEXT

### Monetization (Freemium)

```
Free Tier:
  - 3 photo scans/day
  - Basic calorie + macro tracking
  - 7-day meal history

Premium (₹149/month or ₹999/year):
  - Unlimited scans
  - Full vitamin + mineral tracking
  - Meal suggestions based on gaps
  - Weekly nutrition reports
  - Priority AI processing
  - Unlimited history
```

### Premium Gate Implementation

```python
# In meals.py route handler
user = get_current_user()
if not user.is_premium:
    today_scan_count = await meal_service.count_today_scans(user.id)
    if today_scan_count >= FREE_DAILY_SCAN_LIMIT:  # 3
        raise ForbiddenError(
            message="Free plan allows 3 scans/day. Upgrade to Premium for unlimited.",
            code="PREMIUM_REQUIRED"
        )
```

---

*Last updated: March 2026*
*This document is the source of truth. When in doubt, refer here.*
