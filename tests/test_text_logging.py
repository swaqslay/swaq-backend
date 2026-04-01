"""Tests for text-based meal logging and quick snack shortcut endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


# ── Mock nutrition data ──────────────────────────────────────────────────────

MOCK_NUTRITION = {
    "calories": 180,
    "protein_g": 10,
    "carbs_g": 22,
    "fat_g": 5,
    "fiber_g": 4,
    "vitamins": {},
    "minerals": {},
}


# ── Quick snack catalog tests ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_quick_snacks_list(client: AsyncClient):
    """GET /meals/quick-snacks returns full catalog with categories (no auth)."""
    resp = await client.get("/api/v1/meals/quick-snacks")
    assert resp.status_code == 200
    data = resp.json()["data"]
    snacks = data["snacks"]
    assert len(snacks) >= 15
    # Verify structure of each snack
    for snack in snacks:
        assert "id" in snack
        assert "name" in snack
        assert "emoji" in snack
        assert "calories" in snack
        assert "category" in snack
        assert "default_portion" in snack


# ── Quick snack logging tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quick_snack_log_success(client: AsyncClient, auth_headers: dict):
    """POST /meals/quick-log with valid snack_id returns 201."""
    resp = await client.post(
        "/api/v1/meals/quick-log",
        json={"snack_id": "masala_chai", "quantity": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["ai_provider"] == "quick_snack"
    assert data["ai_model"] == "preset"
    assert data["total_calories"] == 100
    assert len(data["food_items"]) == 1
    assert data["food_items"][0]["name"] == "Masala Chai"


@pytest.mark.asyncio
async def test_quick_snack_log_invalid_id(client: AsyncClient, auth_headers: dict):
    """POST /meals/quick-log with unknown snack_id returns 404."""
    resp = await client.post(
        "/api/v1/meals/quick-log",
        json={"snack_id": "nonexistent_snack"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "QUICK_SNACK_NOT_FOUND"


@pytest.mark.asyncio
async def test_quick_snack_log_quantity(client: AsyncClient, auth_headers: dict):
    """POST /meals/quick-log with quantity=2 doubles nutrition values."""
    resp = await client.post(
        "/api/v1/meals/quick-log",
        json={"snack_id": "masala_chai", "quantity": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["total_calories"] == 200
    assert data["total_protein_g"] == 6.0


@pytest.mark.asyncio
async def test_quick_snack_no_premium_gate(client: AsyncClient, auth_headers: dict):
    """Free user with 3+ scans can still quick-log (no AI cost)."""
    with patch(
        "app.api.v1.meals.meal_service.count_today_scans",
        new_callable=AsyncMock,
    ) as mock_count:
        mock_count.return_value = 3
        resp = await client.post(
            "/api/v1/meals/quick-log",
            json={"snack_id": "banana"},
            headers=auth_headers,
        )
    assert resp.status_code == 201, resp.text


# ── Text-based meal logging tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_log_meal_text_success(client: AsyncClient, profile_headers: dict):
    """POST /meals/log with valid items returns 201 with nutrition."""
    with patch("app.services.meal_service.NutritionLookup") as mock_cls:
        mock_nut = mock_cls.return_value
        mock_nut.get_nutrition_with_cache = AsyncMock(return_value=MOCK_NUTRITION)
        mock_nut.close = AsyncMock()

        resp = await client.post(
            "/api/v1/meals/log",
            json={
                "meal_type": "snack",
                "items": [
                    {"name": "dal", "portion": "1 bowl", "estimated_weight_g": 200},
                ],
                "notes": "evening snack",
            },
            headers=profile_headers,
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["ai_provider"] == "text_input"
    assert data["ai_model"] == "user_reported"
    assert data["total_calories"] > 0
    assert len(data["food_items"]) == 1
    assert data["image_url"] is None


@pytest.mark.asyncio
async def test_log_meal_text_empty_items(client: AsyncClient, auth_headers: dict):
    """POST /meals/log with empty items list returns 422 (Pydantic validation)."""
    resp = await client.post(
        "/api/v1/meals/log",
        json={"meal_type": "snack", "items": []},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_log_meal_text_missing_weight(client: AsyncClient, auth_headers: dict):
    """POST /meals/log with item missing estimated_weight_g returns 422."""
    resp = await client.post(
        "/api/v1/meals/log",
        json={"meal_type": "snack", "items": [{"name": "dal"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_log_meal_text_premium_gate(client: AsyncClient, auth_headers: dict):
    """Free user with 3+ scans today gets 403 on text log."""
    with patch(
        "app.api.v1.meals.meal_service.count_today_scans",
        new_callable=AsyncMock,
    ) as mock_count:
        mock_count.return_value = 3
        resp = await client.post(
            "/api/v1/meals/log",
            json={
                "meal_type": "snack",
                "items": [{"name": "dal", "estimated_weight_g": 200}],
            },
            headers=auth_headers,
        )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PREMIUM_REQUIRED"


@pytest.mark.asyncio
async def test_text_logged_meal_in_history(client: AsyncClient, profile_headers: dict):
    """Text-logged meal appears in GET /meals/history."""
    with patch("app.services.meal_service.NutritionLookup") as mock_cls:
        mock_nut = mock_cls.return_value
        mock_nut.get_nutrition_with_cache = AsyncMock(return_value=MOCK_NUTRITION)
        mock_nut.close = AsyncMock()

        log_resp = await client.post(
            "/api/v1/meals/log",
            json={
                "meal_type": "lunch",
                "items": [
                    {"name": "rice", "portion": "1 plate", "estimated_weight_g": 250},
                ],
            },
            headers=profile_headers,
        )

    assert log_resp.status_code == 201
    meal_id = log_resp.json()["data"]["meal_id"]

    history_resp = await client.get("/api/v1/meals/history", headers=profile_headers)
    assert history_resp.status_code == 200
    meals = history_resp.json()["data"]["meals"]
    assert any(m["id"] == meal_id for m in meals)
