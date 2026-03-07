"""Integration tests for meal endpoints (inline scan model)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# ── Mock data ────────────────────────────────────────────────────────────────

MOCK_COMBINED_RESULT = {
    "food_items": [
        {
            "name": "dal tadka",
            "confidence": 0.91,
            "estimated_portion": "1 bowl",
            "estimated_weight_g": 200,
            "calories": 182,
            "protein_g": 11,
            "carbs_g": 23,
            "fat_g": 5.6,
            "fiber_g": 4.4,
            "vitamins": {},
            "minerals": {},
        },
    ],
    "meal_description": "Dal tadka",
    "cuisine_type": "Indian",
    "_ai_provider": "gemini",
    "_ai_model": "gemini-2.0-flash",
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
    """Create a minimal 10x10 JPEG for upload tests."""
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGB", (10, 10), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ── Mock Redis ────────────────────────────────────────────────────────────────


class MockRedis:
    """Simple dict-backed Redis mock for tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass

    async def aclose(self) -> None:
        pass


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_redis() -> MockRedis:
    return MockRedis()


# ── Scan endpoint tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_requires_auth(client: AsyncClient):
    """POST /meals/scan without auth returns 401."""
    image_bytes = _make_test_image()
    resp = await client.post(
        "/api/v1/meals/scan",
        files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
        data={"meal_type": "lunch"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_scan_invalid_image_type(client: AsyncClient, auth_headers: dict):
    """POST /meals/scan with non-image file returns 400."""
    resp = await client.post(
        "/api/v1/meals/scan",
        files={"image": ("doc.pdf", b"fake pdf content", "application/pdf")},
        data={"meal_type": "lunch"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "MEAL_IMAGE_INVALID"


@pytest.mark.asyncio
async def test_scan_meal_returns_full_result(
    client: AsyncClient,
    profile_headers: dict,
):
    """POST /meals/scan returns 201 with complete MealScanResponse."""
    with (
        patch("app.services.scan_processor.NutritionLookup") as mock_nutrition_cls,
        patch("app.services.scan_processor.AIFoodRecognizer") as mock_recognizer_cls,
        patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_upload,
    ):
        mock_upload.return_value = None

        mock_rec = mock_recognizer_cls.return_value
        mock_rec.analyze_food_image_with_nutrition = AsyncMock(return_value=MOCK_COMBINED_RESULT)
        mock_rec.close = AsyncMock()

        mock_nut = mock_nutrition_cls.return_value
        mock_nut.get_nutrition_with_cache = AsyncMock(return_value=MOCK_NUTRITION_SCALED)
        mock_nut.close = AsyncMock()

        image_bytes = _make_test_image()
        resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
            data={"meal_type": "lunch"},
            headers=profile_headers,
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert "meal_id" in data
    assert data["total_calories"] > 0
    assert len(data["food_items"]) >= 1
    assert data["ai_provider"] == "gemini"
    assert "analyzed_at" in data


@pytest.mark.asyncio
async def test_scan_meal_saved_to_database(
    client: AsyncClient,
    profile_headers: dict,
):
    """POST /meals/scan persists meal + food items in the database."""
    with (
        patch("app.services.scan_processor.NutritionLookup") as mock_nutrition_cls,
        patch("app.services.scan_processor.AIFoodRecognizer") as mock_recognizer_cls,
        patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_upload,
    ):
        mock_upload.return_value = None

        mock_rec = mock_recognizer_cls.return_value
        mock_rec.analyze_food_image_with_nutrition = AsyncMock(return_value=MOCK_COMBINED_RESULT)
        mock_rec.close = AsyncMock()

        mock_nut = mock_nutrition_cls.return_value
        mock_nut.get_nutrition_with_cache = AsyncMock(return_value=MOCK_NUTRITION_SCALED)
        mock_nut.close = AsyncMock()

        image_bytes = _make_test_image()
        scan_resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
            data={"meal_type": "lunch"},
            headers=profile_headers,
        )

    assert scan_resp.status_code == 201, scan_resp.text
    meal_id = scan_resp.json()["data"]["meal_id"]

    # Verify meal appears in history
    history_resp = await client.get("/api/v1/meals/history", headers=profile_headers)
    assert history_resp.status_code == 200
    meals = history_resp.json()["data"]["meals"]
    assert any(m["id"] == meal_id for m in meals)

    # Verify meal detail can be fetched with food items
    detail_resp = await client.get(f"/api/v1/meals/{meal_id}", headers=profile_headers)
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["data"]["food_items"]) == 1


@pytest.mark.asyncio
async def test_scan_works_without_redis(
    client: AsyncClient,
    profile_headers: dict,
):
    """POST /meals/scan succeeds even when Redis is None (caching skipped)."""
    from app.core.redis import get_redis
    from app.main import app

    app.dependency_overrides[get_redis] = lambda: None
    try:
        with (
            patch("app.services.scan_processor.NutritionLookup") as mock_nutrition_cls,
            patch("app.services.scan_processor.AIFoodRecognizer") as mock_recognizer_cls,
            patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_upload,
        ):
            mock_upload.return_value = None

            mock_rec = mock_recognizer_cls.return_value
            mock_rec.analyze_food_image_with_nutrition = AsyncMock(
                return_value=MOCK_COMBINED_RESULT
            )
            mock_rec.close = AsyncMock()

            mock_nut = mock_nutrition_cls.return_value
            mock_nut.get_nutrition_with_cache = AsyncMock(return_value=MOCK_NUTRITION_SCALED)
            mock_nut.close = AsyncMock()

            image_bytes = _make_test_image()
            resp = await client.post(
                "/api/v1/meals/scan",
                files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
                data={"meal_type": "lunch"},
                headers=profile_headers,
            )

        assert resp.status_code == 201, resp.text
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_scan_ai_failure_returns_error(
    client: AsyncClient,
    profile_headers: dict,
):
    """POST /meals/scan returns 503 when all AI providers fail."""
    from app.core.exceptions import ServiceUnavailableError

    with (
        patch("app.services.scan_processor.AIFoodRecognizer") as mock_recognizer_cls,
        patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_upload,
    ):
        mock_upload.return_value = None

        mock_rec = mock_recognizer_cls.return_value
        mock_rec.analyze_food_image_with_nutrition = AsyncMock(
            side_effect=ServiceUnavailableError(
                "All AI providers are temporarily unavailable.", "AI_ALL_PROVIDERS_FAILED"
            )
        )
        mock_rec.close = AsyncMock()

        image_bytes = _make_test_image()
        resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
            data={"meal_type": "lunch"},
            headers=profile_headers,
        )

    assert resp.status_code == 503, resp.text
    assert resp.json()["error"]["code"] == "AI_ALL_PROVIDERS_FAILED"


@pytest.mark.asyncio
async def test_scan_empty_food_list_returns_error(
    client: AsyncClient,
    profile_headers: dict,
):
    """POST /meals/scan returns 400 when AI detects no food items."""
    empty_result = {
        "food_items": [],
        "meal_description": "",
        "cuisine_type": "",
        "_ai_provider": "gemini",
        "_ai_model": "gemini-2.0-flash",
    }

    with (
        patch("app.services.scan_processor.AIFoodRecognizer") as mock_recognizer_cls,
        patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_upload,
    ):
        mock_upload.return_value = None

        mock_rec = mock_recognizer_cls.return_value
        mock_rec.analyze_food_image_with_nutrition = AsyncMock(return_value=empty_result)
        mock_rec.close = AsyncMock()

        image_bytes = _make_test_image()
        resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
            data={"meal_type": "lunch"},
            headers=profile_headers,
        )

    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "MEAL_SCAN_FAILED"


@pytest.mark.asyncio
async def test_scan_includes_recommendations_with_profile(
    client: AsyncClient,
    profile_headers: dict,
):
    """POST /meals/scan populates recommendations when user has a profile."""
    with (
        patch("app.services.scan_processor.NutritionLookup") as mock_nutrition_cls,
        patch("app.services.scan_processor.AIFoodRecognizer") as mock_recognizer_cls,
        patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_upload,
    ):
        mock_upload.return_value = None

        mock_rec = mock_recognizer_cls.return_value
        mock_rec.analyze_food_image_with_nutrition = AsyncMock(return_value=MOCK_COMBINED_RESULT)
        mock_rec.close = AsyncMock()

        mock_nut = mock_nutrition_cls.return_value
        mock_nut.get_nutrition_with_cache = AsyncMock(return_value=MOCK_NUTRITION_SCALED)
        mock_nut.close = AsyncMock()

        image_bytes = _make_test_image()
        resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
            data={"meal_type": "lunch"},
            headers=profile_headers,
        )

    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)


@pytest.mark.asyncio
async def test_premium_gate_blocks_4th_scan(
    client: AsyncClient,
    auth_headers: dict,
):
    """Free users are blocked after 3 scans per day."""
    with (
        patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_up,
        patch(
            "app.api.v1.meals.meal_service.count_today_scans",
            new_callable=AsyncMock,
        ) as mock_count,
    ):
        mock_up.return_value = None
        mock_count.return_value = 3

        image_bytes = _make_test_image()
        resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
            data={"meal_type": "snack"},
            headers=auth_headers,
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "PREMIUM_REQUIRED"


# ── Non-scan meal tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_meal_history_empty(client: AsyncClient, auth_headers: dict):
    """GET /meals/history returns empty list when no meals exist."""
    resp = await client.get("/api/v1/meals/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["meals"] == []


@pytest.mark.asyncio
async def test_get_nonexistent_meal(client: AsyncClient, auth_headers: dict):
    """GET /meals/{id} returns 404 for unknown meal."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/meals/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "MEAL_NOT_FOUND"
