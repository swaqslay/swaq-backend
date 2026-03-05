# Architecture Rules — Swaq AI Backend

## Tech Stack

- **Runtime**: Python 3.10+ with FastAPI 0.115+
- **ORM**: SQLAlchemy 2.0 async with Mapped types
- **Migrations**: Alembic
- **Validation**: Pydantic 2.10+
- **Server**: Uvicorn (ASGI)
- **HTTP Client**: httpx (async only — NEVER use `requests`)
- **Database**: PostgreSQL 16+ (Supabase free tier)
- **Cache**: Redis 7+ (Upstash free tier)
- **AI Primary**: Google Gemini 2.0 Flash via `google-genai` SDK
- **AI Fallback**: OpenRouter via `openai` client (OpenAI-compatible API, free vision models)
- **Nutrition DB**: USDA FoodData Central REST API
- **Image Storage**: Backblaze B2 (S3-compatible, active) / Cloudflare R2 (reserved for future use)
- **Auth**: JWT (HS256) — 15-min access tokens + 30-day refresh tokens
- **Password Hashing**: bcrypt (12 rounds)

## Project Layout

```
swaq-backend/
├── app/
│   ├── main.py              # FastAPI app factory + lifespan
│   ├── core/                # Framework-level config
│   │   ├── config.py        # Pydantic Settings (env vars)
│   │   ├── database.py      # Async engine + session factory
│   │   ├── redis.py         # Redis connection pool
│   │   ├── security.py      # JWT + password hashing
│   │   └── exceptions.py    # SwaqError hierarchy + handlers
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response DTOs
│   ├── api/                 # Thin route handlers (controllers)
│   │   ├── router.py        # Main router aggregator
│   │   ├── v1/              # Versioned endpoints
│   │   └── deps.py          # get_current_user, get_db, get_redis
│   ├── services/            # ALL business logic lives here
│   └── utils/               # Prompts, constants, helpers
├── tests/
├── alembic/
├── scripts/
├── docker/
└── agent_utils/            # Ad-hoc verification & debug scripts
```

## Dependency Direction (CRITICAL)

Dependencies flow ONE direction only:

```
api/ (routes) --> services/ --> models/
                             --> external APIs (via httpx)
```

### Absolute Rules

1. **NEVER put business logic in route handlers (`api/`)**. Routes are THIN: validate input, call a service, return the response
2. **NEVER import from `api/` in `services/`**. No reverse dependencies
3. **NEVER access the `request` object in services**. Pass only the data the service needs
4. **ALL database queries go through services**, not directly in route handlers
5. **ALL external API calls go through services** with proper error handling and fallback

## Response Envelope

All API responses use the standard envelope:

```python
APIResponse[T] = {"success": bool, "data": T | None, "error": ErrorDetail | None}
```

## API Versioning

All endpoints prefixed with `/api/v1/`. Breaking changes require a new version.

## Database Models

Five core tables: `users`, `user_profiles`, `meals`, `meal_food_items`, `nutrition_cache`

- All UUIDs use `uuid.uuid4()` as default
- All timestamps are UTC with `func.now()` server defaults
- Micronutrients (vitamins, minerals) stored as JSON on `MealFoodItem` for flexibility

## AI Pipeline Architecture

Two-step pipeline for food recognition:

1. **Step 1 — Visual Identification** (vision model): Photo -> list of food items + portions + confidence
2. **Step 2 — Nutrition Estimation** (text model): Food items -> complete nutritional profile

Provider failover: Gemini Flash -> OpenRouter models (Qwen3-VL -> Gemma 3 -> Nemotron -> auto-router) -> ServiceUnavailableError

## Three-Tier Nutrition Cache

1. **Redis** (TTL 7 days) -> 2. **PostgreSQL nutrition_cache** (permanent) -> 3. **USDA API / AI estimation** (external)

## Async Rules

- ALL database operations must be `async def` + `await`
- ALL external HTTP calls must use `httpx.AsyncClient`
- NEVER use `time.sleep()` — use `asyncio.sleep()` if needed
- NEVER use synchronous `requests` library
