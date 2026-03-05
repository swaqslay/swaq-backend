# Dependencies Rules — Swaq AI Backend

Load this file when adding or updating packages.

## 1. Before Adding a Package

Verify: active maintenance, reasonable adoption, acceptable license (MIT/Apache/BSD), no critical vulnerabilities.

## 2. No Micro-Dependencies

If it can be done in ~30 lines of Python, write it. Don't install a package for trivial operations.

## 3. Check Existing Dependencies First

No duplicate packages solving the same problem. The project already uses:
- `httpx` for HTTP (don't add `requests` or `aiohttp`)
- `pydantic` for validation (don't add `marshmallow` or `cerberus`)
- `passlib[bcrypt]` for password hashing
- `python-jose[cryptography]` for JWT
- `Pillow` for image processing
- `google-genai` for Gemini API calls (don't add raw REST calls via `httpx` for Gemini)
- `openai` for OpenRouter (OpenAI-compatible API; don't add a separate OpenRouter client)
- `ruff` for linting + formatting

## 4. Core Dependencies

```
# Web framework
fastapi >= 0.115
uvicorn >= 0.34
python-multipart

# AI & ML
google-genai       # Google Gemini SDK (primary AI provider)
openai >= 1.60     # OpenRouter client (OpenAI-compatible API)
httpx >= 0.28      # Async HTTP for USDA + Gemini REST fallback
Pillow             # Image resize + EXIF strip

# Database
sqlalchemy >= 2.0
alembic >= 1.14
asyncpg            # PostgreSQL async driver (production)
aiosqlite          # SQLite async driver (tests / local dev)

# Validation & config
pydantic >= 2.10
pydantic-settings

# Auth
python-jose[cryptography]
passlib[bcrypt]

# Cache
redis[asyncio]     # Async Redis client

# Storage
boto3              # Backblaze B2 / Cloudflare R2 (S3-compatible)
```

## 5. Dev Dependencies

```
pytest >= 8.3
pytest-asyncio
ruff
```

## 6. Lockfile

Use `pip freeze > requirements.txt` or `pyproject.toml` with pinned versions for reproducible builds.

## 7. Security Audit

Before merging dependency changes, run `pip audit` to check for known vulnerabilities.
