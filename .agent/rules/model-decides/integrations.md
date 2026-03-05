# Integrations Rules — Swaq AI Backend

Load this file when working on external API integrations (Gemini, OpenRouter, USDA, Cloudflare R2).

## 1. Timeouts

Explicit connect and read timeouts on every outbound HTTP call:

```python
async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=30.0)) as client:
    response = await client.post(...)
```

## 2. Adapter Isolation

Each external service is isolated in its own service module:
- `app/services/ai_food_recognizer.py` — Gemini (via `google-genai` SDK) + OpenRouter fallback
- `app/services/nutrition_lookup.py` — USDA FoodData Central + caching
- `app/services/image_storage.py` — Backblaze B2 (S3-compatible via `boto3`)

## 3. Backblaze B2 (Active Image Storage)

S3-compatible API via `boto3`:
- Endpoint from `BACKBLAZE_B2_ENDPOINT` (format: `https://s3.<region>.backblazeb2.com`)
- Bucket from `BACKBLAZE_B2_BUCKET`
- Access key from `BACKBLAZE_B2_ACCESS_KEY` / `BACKBLAZE_B2_SECRET_KEY`
- Generate presigned URLs for Flutter app to display images (1-hour expiry)

> **Cloudflare R2** credentials (`CLOUDFLARE_R2_*`) are in config but reserved for future use. Do not add new code targeting R2 without explicit instruction.

## 4. USDA FoodData Central

```
Base URL: https://api.nal.usda.gov/fdc/v1
Rate limit: 1,000 requests/hour
Data types: "Foundation" and "SR Legacy"
```

Key nutrient IDs defined in `app/utils/constants.py`.

## 5. Logging

Log every outbound request with:
- Service name (gemini, openrouter, usda, r2)
- HTTP method and URL
- Response status code
- Duration (ms)
- Error details if failed

## 6. Graceful Degradation

- Gemini down -> OpenRouter fallback chain
- USDA down -> PostgreSQL cache -> AI estimation
- Redis down -> PostgreSQL cache -> external API
- R2 down -> meal saved without image URL

## 7. API Key Rotation

Design for zero-downtime key rotation. Keys come from env vars; no hardcoded values.
