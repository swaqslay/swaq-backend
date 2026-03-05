# Documentation Rules — Swaq AI Backend

Load this file when working on API docs, README, or inline comments.

## 1. Docstrings

Google-style docstrings on all public Python functions, classes, and modules:

```python
def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Calculate Body Mass Index from weight and height.

    Args:
        weight_kg: User's weight in kilograms.
        height_cm: User's height in centimeters.

    Returns:
        BMI value as a float.

    Raises:
        ValidationError: If weight or height is non-positive.
    """
```

## 2. Inline Comments

Comments explain *why*, never *what*. The code should be self-explanatory for *what*.

```python
# Good: Resize to 1536px max — saves AI tokens without quality loss for food recognition
# Bad: Resize the image to 1536 pixels
```

## 3. API Documentation

Auto-generated from FastAPI's OpenAPI spec. Keep Pydantic schema docstrings accurate as they appear in Swagger UI.

## 4. CLAUDE.md

`CLAUDE.md` is the project bible. Update it in the same PR as changes it describes. It documents:
- Project structure
- Database schema
- API specification
- AI pipeline architecture
- Auth flow
- Error codes

## 5. .env.example

Keep `.env.example` in sync with `app/core/config.py`. Every required environment variable must have a placeholder and brief description.
