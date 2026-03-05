# Performance Rules — Swaq AI Backend

Load this file when working on DB queries, pagination, or response-time-sensitive paths.

## 1. No N+1 Queries

Use `selectinload()` or `joinedload()` when loading relationships. Never iterate and query inside a loop.

## 2. Denormalized Totals

Meal records store denormalized nutrition totals (`total_calories`, `total_protein_g`, etc.) for fast dashboard queries. Recalculate these when food items are added, edited, or deleted.

## 3. Three-Tier Cache

Nutrition lookups follow the cache hierarchy:
1. Redis (TTL 7 days, ~1ms)
2. PostgreSQL nutrition_cache (permanent, ~5ms)
3. External API / AI estimation (~200-500ms)

This reduces USDA API calls by ~70% after warm-up.

## 4. Indexes

Required indexes for query-hot paths:
- `meals(user_id, created_at DESC)` — dashboard queries
- `nutrition_cache(food_name_normalized)` — cache lookups
- `users(email)` — login lookups

## 5. Image Optimization

Resize images to max 1536px on longest edge before sending to AI. Saves tokens without quality loss for food recognition.

## 6. Pagination

Meal history endpoints support date-based filtering:
- `?date=YYYY-MM-DD` for single day
- `?from=&to=` for date ranges
- Default sort: `created_at DESC`

## 7. Measure Before Optimizing

Don't add Redis caching or denormalization without an observed performance problem. The three-tier cache for nutrition data is justified; don't add caching elsewhere without evidence.

## 8. Redis TTLs

```
nutrition:{name}           — 7 days
usda_search:{hash}         — 24 hours
user_daily:{user_id}:{date} — 1 hour
rate_limit:{endpoint}:{ip}  — 60 seconds
```
