# Database Rules — Swaq AI Backend

Load this file when working on migrations, SQLAlchemy models, or transaction boundaries.

## 1. Database Engine

PostgreSQL 16+ via Supabase. Async SQLAlchemy 2.0 with `asyncpg` driver. Session factory in `app/core/database.py`.

## 2. ORM Style

SQLAlchemy 2.0 Mapped types:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
```

## 3. Core Tables

- `users` — Account data (email, name, hashed_password, is_premium)
- `user_profiles` — Body profile + computed targets (BMI, daily calories, macro targets)
- `meals` — Meal records with denormalized nutrition totals + AI metadata
- `meal_food_items` — Individual food items with macros + micronutrient JSON
- `nutrition_cache` — Cached USDA/AI nutrition lookups

## 4. Migrations

Alembic in `alembic/` directory. Every schema change requires a migration:

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

Every migration must have a working `downgrade()`. Schema changes must be backward-compatible with deployed code.

## 5. Data Integrity at Schema Level

- `nullable=False` on all required fields
- Foreign keys with `ondelete="CASCADE"` for dependent records
- Unique constraints on `users.email`, `user_profiles.user_id`, `nutrition_cache.food_name_normalized`
- Indexes on query-hot columns: `meals(user_id, created_at DESC)`, `nutrition_cache(food_name_normalized)`

## 6. Timestamps

Every table gets:
- `created_at` with `default=func.now()` (server-side UTC)
- `updated_at` with `default=func.now(), onupdate=func.now()` where applicable

## 7. JSON Columns

Micronutrients stored as JSON on `MealFoodItem`:
- `vitamins`: `{"vitamin_c": {"amount": 15.2, "unit": "mg", "dv_percent": 16.9}, ...}`
- `minerals`: `{"iron": {"amount": 2.1, "unit": "mg", "dv_percent": 11.7}, ...}`
- `dietary_restrictions` on `UserProfile`: JSON array of strings

## 8. Query Patterns

- Services own transaction scope — routes don't manage sessions directly
- Use `select()` statements (SQLAlchemy 2.0 style), not legacy `query()`
- Avoid N+1 queries — use `selectinload()` for relationships when needed
- All queries are async: `await session.execute(stmt)`

## 9. Naming

- Table names: `snake_case`, plural (`users`, `meals`, `meal_food_items`)
- Column names: `snake_case`, singular (`user_id`, `created_at`)
- Model classes: PascalCase, singular (`User`, `Meal`, `MealFoodItem`)
