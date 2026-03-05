# Error Handling Rules — Swaq AI Backend

Load this file when working on retry logic, failure recovery, or external API calls.

## 1. SwaqError Hierarchy

All domain errors extend `SwaqError` in `app/core/exceptions.py`:

```python
SwaqError(Exception)            # Base (500)
├── ValidationError             # 400
├── AuthenticationError         # 401
├── ForbiddenError              # 403
├── NotFoundError               # 404
├── RateLimitError              # 429
├── AIProviderError             # 502
└── ServiceUnavailableError     # 503
```

## 2. Error Response Format

Single global exception handler maps `SwaqError` to JSON:

```json
{"success": false, "data": null, "error": {"code": "ERROR_CODE", "message": "Human-readable message"}}
```

User-facing messages reveal no internal state. Internal logs include full context.

## 3. Error Codes

Use the standard error code set:
- `AUTH_INVALID_CREDENTIALS`, `AUTH_TOKEN_EXPIRED`, `AUTH_TOKEN_INVALID`, `AUTH_EMAIL_EXISTS`
- `PROFILE_NOT_FOUND`, `PROFILE_INVALID_DATA`
- `MEAL_NOT_FOUND`, `MEAL_SCAN_FAILED`, `MEAL_IMAGE_INVALID`, `MEAL_IMAGE_TOO_LARGE`
- `AI_ALL_PROVIDERS_FAILED`, `AI_INVALID_RESPONSE`
- `NUTRITION_LOOKUP_FAILED`
- `RATE_LIMIT_EXCEEDED`, `INTERNAL_ERROR`

## 4. AI Provider Failover

Retry logic for AI calls follows the failover chain:

```
Gemini Flash -> Qwen3-VL (OpenRouter) -> Gemma 3 -> Nemotron -> openrouter/free -> ServiceUnavailableError
```

- Retry only on transient failures: 429, 500, 502-504, timeouts
- Each provider gets ONE attempt (no retry within same provider)
- Log each failure with provider name, status code, and error message

## 5. USDA API Failures

If USDA lookup fails:
- Check PostgreSQL nutrition_cache (permanent fallback)
- Use AI-estimated nutrition data from Step 2 (already calculated)
- Never block the meal scan response due to USDA unavailability

## 6. Never Swallow Errors

- No empty `except:` blocks
- No `except Exception: pass`
- Every caught exception must be logged or re-raised
- Log with structured data: `logger.error("USDA lookup failed", extra={"food_name": name, "status": status})`

## 7. Graceful Degradation

- AI unavailable: Return `ServiceUnavailableError` with clear message
- Redis unavailable: Fall through to PostgreSQL cache, then external API
- USDA unavailable: Use AI-estimated values (already in pipeline)
- R2 unavailable: Store image URL as None, still process AI recognition from uploaded bytes
