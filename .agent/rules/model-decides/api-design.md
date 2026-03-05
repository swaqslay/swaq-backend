# API Design Rules — Swaq AI Backend

Load this file when working on REST endpoints, Pydantic DTOs, or API contracts.

## 1. Response Envelope

All endpoints use `APIResponse[T]`:

```json
{"success": true, "data": {...}, "error": null}
{"success": false, "data": null, "error": {"code": "ERROR_CODE", "message": "Human-readable"}}
```

## 2. HTTP Status Codes

- `200` — Success (GET, PATCH)
- `201` — Created (POST register, POST profile, POST scan)
- `204` — No content (DELETE)
- `400` — Validation error
- `401` — Authentication failed (invalid/expired token)
- `403` — Forbidden (premium required, wrong user)
- `404` — Resource not found
- `429` — Rate limit exceeded
- `502` — AI provider error
- `503` — All AI providers unavailable

## 3. Pydantic DTOs

- Request/response DTOs for ALL endpoints — never expose SQLAlchemy models directly
- Schemas live in `app/schemas/` organized by domain (auth, user, meal, nutrition, dashboard)
- Use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility

## 4. Endpoint Naming

- All endpoints prefixed with `/api/v1/`
- Resource naming: plural nouns, lowercase, hyphens for multi-word
- Non-CRUD actions use verb sub-resources: `/meals/scan`, `/auth/refresh`
- Collection endpoints: `/meals/history?date=2025-03-15&from=&to=`

## 5. Pagination

Collection endpoints support query parameters:
- `?date=YYYY-MM-DD` for single-day queries
- `?from=YYYY-MM-DD&to=YYYY-MM-DD` for date ranges
- Results ordered by `created_at DESC` by default

## 6. Error Codes

Use machine-readable error codes from the standard set:
- `AUTH_*` — Authentication/authorization errors
- `PROFILE_*` — Profile-related errors
- `MEAL_*` — Meal scanning/CRUD errors
- `AI_*` — AI provider errors
- `NUTRITION_*` — Nutrition lookup errors
- `RATE_LIMIT_EXCEEDED` — Rate limiting
- `INTERNAL_ERROR` — Unexpected server error

## 7. Auth Headers

Protected endpoints require `Authorization: Bearer <access_token>` header. The `get_current_user` dependency in `app/api/deps.py` handles token verification and user injection.

## 8. File Uploads

Meal photo uploads via `multipart/form-data`:
- Accept: JPEG, PNG, WebP only
- Max size: 10MB
- Additional form fields: `meal_type` (breakfast/lunch/dinner/snack)
