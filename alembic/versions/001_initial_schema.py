"""Initial schema: users, user_profiles, meals, meal_food_items, nutrition_cache

Revision ID: 001
Revises:
Create Date: 2026-03-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_premium", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── user_profiles ─────────────────────────────────────────────────────────
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("gender", sa.String(10), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("activity_level", sa.String(20), server_default="moderate"),
        sa.Column("health_goal", sa.String(20), server_default="maintain"),
        sa.Column("dietary_restrictions", sa.JSON(), server_default="[]"),
        sa.Column("bmi", sa.Float(), nullable=False),
        sa.Column("daily_calorie_target", sa.Integer(), nullable=False),
        sa.Column("daily_protein_target_g", sa.Integer(), nullable=False),
        sa.Column("daily_carb_target_g", sa.Integer(), nullable=False),
        sa.Column("daily_fat_target_g", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    # ── meals ─────────────────────────────────────────────────────────────────
    op.create_table(
        "meals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meal_type", sa.String(20), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total_calories", sa.Float(), server_default="0"),
        sa.Column("total_protein_g", sa.Float(), server_default="0"),
        sa.Column("total_carbs_g", sa.Float(), server_default="0"),
        sa.Column("total_fat_g", sa.Float(), server_default="0"),
        sa.Column("total_fiber_g", sa.Float(), server_default="0"),
        sa.Column("ai_provider", sa.String(20), nullable=True),
        sa.Column("ai_model", sa.String(100), nullable=True),
        sa.Column("ai_confidence_avg", sa.Float(), server_default="0"),
        sa.Column("is_manually_edited", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meals_user_id", "meals", ["user_id"])
    op.create_index("idx_meals_user_date", "meals", ["user_id", "created_at"])

    # ── meal_food_items ───────────────────────────────────────────────────────
    op.create_table(
        "meal_food_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("meal_id", sa.Uuid(), sa.ForeignKey("meals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8"),
        sa.Column("estimated_portion", sa.String(100), server_default="1 serving"),
        sa.Column("estimated_weight_g", sa.Float(), nullable=False),
        sa.Column("calories", sa.Float(), server_default="0"),
        sa.Column("protein_g", sa.Float(), server_default="0"),
        sa.Column("carbs_g", sa.Float(), server_default="0"),
        sa.Column("fat_g", sa.Float(), server_default="0"),
        sa.Column("fiber_g", sa.Float(), server_default="0"),
        sa.Column("vitamins", sa.JSON(), server_default="{}"),
        sa.Column("minerals", sa.JSON(), server_default="{}"),
        sa.Column("usda_fdc_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_meal_food_items_meal_id", "meal_food_items", ["meal_id"])

    # ── nutrition_cache ───────────────────────────────────────────────────────
    op.create_table(
        "nutrition_cache",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("food_name_normalized", sa.String(200), nullable=False),
        sa.Column("usda_fdc_id", sa.Integer(), nullable=True),
        sa.Column("nutrition_data", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_nutrition_cache_name", "nutrition_cache", ["food_name_normalized"], unique=True)


def downgrade() -> None:
    op.drop_table("nutrition_cache")
    op.drop_table("meal_food_items")
    op.drop_table("meals")
    op.drop_table("user_profiles")
    op.drop_table("users")
