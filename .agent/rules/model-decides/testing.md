# Testing Rules — Swaq AI Backend

Load this file when writing tests or working on code that requires test coverage.

## 1. Ship Tests With Code

Every user-facing feature, business logic branch, and bug fix ships with tests in the same unit of work. Tests are not a separate step.

## 2. Test Naming

Python test names: `test_[unit]_[scenario]_[expected_result]`

Examples:
- `test_bmi_calculation_obese_returns_correct_category`
- `test_login_wrong_password_returns_401`
- `test_scan_free_user_exceeds_limit_returns_403`

## 3. Test Database

Use SQLite in-memory for tests (fast, isolated):

```python
engine = create_async_engine("sqlite+aiosqlite:///:memory:")
```

Override `get_db` dependency in test fixtures.

## 4. Integration Tests

Cover critical paths end-to-end:
- Register -> login -> get token -> access protected endpoint
- Create profile -> verify BMI and targets calculated
- Upload food photo -> get meal analysis (mock AI response)
- Get daily dashboard -> verify aggregation
- Manual meal correction -> verify totals recalculated
- Rate limiting works correctly
- Invalid token -> 401

## 5. Mock Only External Dependencies

Mock external APIs (Gemini, OpenRouter, USDA, Cloudflare R2). Never mock own services, repositories, or database sessions.

Key mocking patterns:
- Patch `app.services.ai_food_recognizer.preprocess_image` since tests use fake bytes
- Patch `httpx.AsyncClient` for external API calls
- Use `app.dependency_overrides` for dependency injection in tests

## 6. AI Service Tests

- Gemini success -> returns structured result
- Gemini fails -> falls back to OpenRouter
- Both fail -> returns ServiceUnavailableError
- AI returns invalid JSON -> graceful error
- AI returns empty food list -> MEAL_SCAN_FAILED

## 7. Test Isolation

Each test creates and destroys its own state. No test depends on execution order. Use fresh in-memory database per test session.

## 8. Assert on Outputs

Assert on HTTP responses, return values, and observable DB state — not on internal call counts.

## 9. Running Tests

```bash
# All tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=html

# Specific file
python -m pytest tests/test_meals.py -v
```

## 10. Key Test Fixtures

Defined in `tests/conftest.py`:
- `test_db` — Fresh SQLite in-memory database
- `test_client` — FastAPI AsyncClient with overridden DB
- `auth_headers` — Pre-authenticated headers for protected endpoints
