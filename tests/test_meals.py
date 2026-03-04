"""Integration tests for meal endpoints."""

import uuid
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


MOCK_AI_RECOGNITION = {
    "food_items": [
        {"name": "dal tadka", "confidence": 0.91, "estimated_portion": "1 bowl", "estimated_weight_g": 200},
    ],
    "meal_description": "Dal tadka",
    "cuisine_type": "Indian",
    "_ai_provider": "gemini",
    "_ai_model": "gemini-2.0-flash",
}

MOCK_AI_NUTRITION = {
    "food_items": [
        {
            "name": "dal tadka",
            "estimated_weight_g": 200,
            "calories": 182,
            "protein_g": 11,
            "carbs_g": 23,
            "fat_g": 5.6,
            "fiber_g": 4.4,
            "vitamins": [],
            "minerals": [],
        }
    ]
}

MOCK_NUTRITION_SCALED = {
    "calories": 182,
    "protein_g": 11,
    "carbs_g": 23,
    "fat_g": 5.6,
    "fiber_g": 4.4,
    "vitamins": {},
    "minerals": {},
}


def _make_test_image() -> bytes:
    """Create a minimal 1×1 JPEG for upload tests."""
    from PIL import Image
    from io import BytesIO
    img = Image.new("RGB", (10, 10), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_scan_meal_success(client: AsyncClient, profile_headers: dict):
    with (
        patch("app.api.v1.meals.AIFoodRecognizer") as MockRecognizer,
        patch("app.api.v1.meals.NutritionLookup") as MockNutrition,
        patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_upload,
    ):
        mock_rec = MockRecognizer.return_value
        mock_rec.analyze_food_image = AsyncMock(return_value=MOCK_AI_RECOGNITION)
        mock_rec.estimate_nutrition = AsyncMock(return_value=MOCK_AI_NUTRITION)

        mock_nut = MockNutrition.return_value
        mock_nut.get_nutrition_with_cache = AsyncMock(return_value=MOCK_NUTRITION_SCALED)

        mock_upload.return_value = None

        image_bytes = _make_test_image()
        resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
            data={"meal_type": "lunch"},
            headers=profile_headers,
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["total_calories"] > 0
    assert len(data["food_items"]) == 1
    assert data["food_items"][0]["name"] == "dal tadka"
    assert "meal_id" in data


@pytest.mark.asyncio
async def test_scan_requires_auth(client: AsyncClient):
    image_bytes = _make_test_image()
    resp = await client.post(
        "/api/v1/meals/scan",
        files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
        data={"meal_type": "lunch"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_scan_invalid_image_type(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/meals/scan",
        files={"image": ("doc.pdf", b"fake pdf content", "application/pdf")},
        data={"meal_type": "lunch"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "MEAL_IMAGE_INVALID"


@pytest.mark.asyncio
async def test_meal_history_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/meals/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["meals"] == []


@pytest.mark.asyncio
async def test_get_nonexistent_meal(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/meals/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "MEAL_NOT_FOUND"


@pytest.mark.asyncio
async def test_premium_gate_blocks_4th_scan(client: AsyncClient, auth_headers: dict):
    """Free users are blocked after 3 scans per day."""
    with (
        patch("app.api.v1.meals.AIFoodRecognizer") as MockR,
        patch("app.api.v1.meals.NutritionLookup") as MockN,
        patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_up,
    ):
        mock_r = MockR.return_value
        mock_r.analyze_food_image = AsyncMock(return_value=MOCK_AI_RECOGNITION)
        mock_r.estimate_nutrition = AsyncMock(return_value=MOCK_AI_NUTRITION)
        mock_n = MockN.return_value
        mock_n.get_nutrition_with_cache = AsyncMock(return_value=MOCK_NUTRITION_SCALED)
        mock_up.return_value = None

        image_bytes = _make_test_image()

        # 3 successful scans
        for _ in range(3):
            resp = await client.post(
                "/api/v1/meals/scan",
                files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
                data={"meal_type": "snack"},
                headers=auth_headers,
            )
            assert resp.status_code == 201, f"Scan failed: {resp.text}"

        # 4th scan should be blocked
        resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
            data={"meal_type": "snack"},
            headers=auth_headers,
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "PREMIUM_REQUIRED"
