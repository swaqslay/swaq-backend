# Environment Rules — Swaq AI Backend

Load this file when working on env vars, config, or deployment settings.

## 1. Configuration Source

All config via `pydantic-settings` in `app/core/config.py`. Never read `os.environ` directly.

## 2. Fail Fast

Parse and validate all env vars at startup. Missing or invalid vars cause immediate startup failure with a clear error message.

## 3. Separate Config From Secrets

**Config** (features, limits, log levels):
- `APP_ENV` (development/staging/production)
- `FREE_DAILY_SCAN_LIMIT` (default: 3)
- `LOG_LEVEL` (default: INFO)

**Secrets** (credentials):
- `SECRET_KEY` — JWT signing key
- `DATABASE_URL` — PostgreSQL connection string
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_ANON_KEY` — Supabase anonymous key
- `REDIS_URL` — Redis connection string
- `GEMINI_API_KEY` — Google Gemini API key
- `OPENROUTER_API_KEY` — OpenRouter API key
- `USDA_API_KEY` — USDA FoodData Central API key
- `BACKBLAZE_B2_ENDPOINT` — B2 S3-compatible endpoint URL
- `BACKBLAZE_B2_ACCESS_KEY` — B2 application key ID
- `BACKBLAZE_B2_SECRET_KEY` — B2 application key
- `BACKBLAZE_B2_BUCKET` — B2 bucket name
- `BACKBLAZE_B2_REGION` — B2 region (e.g. us-west-004)

> **Note**: Cloudflare R2 credentials (`CLOUDFLARE_R2_*`) are reserved for future use. Backblaze B2 is the active image storage provider.

## 4. .env.example

Maintain `.env.example` listing every required variable with placeholder values and brief descriptions. Keep this file in sync with `app/core/config.py`.

## 5. Production Defaults

Production defaults must be safe:
- Debug off
- Strict CORS (explicit origins only)
- HTTPS-only
- Verbose logging off

## 6. Access Config

Always through the centralized `Settings` class:

```python
from app.core.config import settings
api_key = settings.gemini_api_key
```

Never import `os` to read environment variables in application code.

## 7. Local Development

```bash
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload --port 8000
```
