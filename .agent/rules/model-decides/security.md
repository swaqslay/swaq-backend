# Security Rules — Swaq AI Backend

Load this file when working on authentication, authorization, user input handling, or external-facing endpoints.

## 1. Input Validation

Validate all external input at API boundary via Pydantic schemas. Never pass unvalidated data to services.

## 2. Authentication

- JWT-based auth with HS256 algorithm
- Access tokens: 15-minute expiry
- Refresh tokens: 30-day expiry
- Token in `Authorization: Bearer <token>` header
- `get_current_user` dependency in `app/api/deps.py` handles verification

## 3. Password Security

- Hash with bcrypt, 12 salt rounds
- Minimum 8 characters
- NEVER store in plaintext, NEVER log, NEVER return in API responses
- Use `passlib[bcrypt]` via `app/core/security.py`

## 4. Secrets Management

- All secrets from environment variables via `pydantic-settings`
- NEVER hardcode API keys, database URLs, or JWT secrets
- NEVER log sensitive values (passwords, tokens, API keys)
- `.env` file NEVER committed (in `.gitignore`)

## 5. CORS

Explicit allowed origins only — never wildcard in staging/production:

```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://swaq.app",
]
```

## 6. Rate Limiting

Rate-limit all public endpoints:
- `/auth/register`: 5/minute (prevent spam)
- `/auth/login`: 10/minute (prevent brute force)
- `/meals/scan`: 30/minute (AI cost protection)
- Default: 100/minute

## 7. Security Headers

All responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

## 8. Premium Gate

Free users limited to 3 scans/day. Enforcement in route handler before calling service:

```python
if not user.is_premium:
    count = await meal_service.count_today_scans(user.id)
    if count >= 3:
        raise ForbiddenError(message="...", code="PREMIUM_REQUIRED")
```

## 9. Image Upload Security

- Validate MIME type (JPEG, PNG, WebP only)
- Max 10MB file size
- Strip EXIF metadata (privacy — no GPS coordinates)
- Generate unique filenames (prevent path traversal)

## 10. SQL Injection Prevention

SQLAlchemy ORM with parameterized queries only. No raw SQL string concatenation.

## 11. Fail Closed

Deny access by default. Only unauthenticated endpoints: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/google`, `/health`, `/health/ready`.
