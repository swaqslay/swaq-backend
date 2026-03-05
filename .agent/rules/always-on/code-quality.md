# Code Quality Rules — Swaq AI Backend

## 1. Type Safety

- Explicit type annotations on ALL function signatures — no exceptions
- Use `Mapped[]` types for SQLAlchemy models (SQLAlchemy 2.0 style)
- Use Pydantic models for all API request/response shapes
- No `Any` type in production code unless absolutely unavoidable

## 2. Pydantic v2 Validation

- Runtime validation for all API request/response shapes via Pydantic 2.10+
- Configuration via `pydantic-settings` (never raw `os.environ`)
- All schemas in `app/schemas/` — never expose SQLAlchemy models directly in API responses

## 3. No Magic Values

Every behavior-controlling literal gets a named constant in `app/utils/constants.py`:
- Daily values (RDA), activity multipliers, macro splits
- Free tier limits (3 scans/day)
- Token expiry times (15 min access, 30 day refresh)
- Image size limits (10MB max, 1536px resize threshold)

## 4. Error Handling

- Never swallow errors — log with structured data or re-raise
- No empty `except:` blocks
- Use `SwaqError` subclasses for expected failures (see `app/core/exceptions.py`)
- Reserve bare exceptions for truly unexpected errors

## 5. System Boundary Validation

- Pydantic validates at every FastAPI endpoint (request body, query params)
- Image validation at upload boundary (format, size, MIME type)
- AI response validation after JSON parsing (expected schema check)
- Never pass unvalidated external data deeper into the system

## 6. Naming Conventions

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
```

## 7. Python Style

- **Formatter**: Ruff (`ruff format`)
- **Linter**: Ruff (`ruff check`)
- **Line length**: 100 characters max
- **Quotes**: Double quotes for strings
- **Imports**: Absolute imports only. Group: stdlib -> third-party -> local. Sorted alphabetically
- **Docstrings**: Google style on all public functions, classes, and modules

## 8. Shared Abstractions

Extract only after the third use case arrives. Premature DRY across services creates harmful coupling. Three similar lines of code is acceptable.

## 9. Async Consistency

- ALL database operations: `async def` + `await`
- ALL external HTTP calls: `httpx.AsyncClient` (never `requests`)
- NEVER `time.sleep()` — use `asyncio.sleep()` if needed
