"""Integration tests for meal endpoints (async scan model)."""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.scan_worker import SCAN_KEY_PREFIX

# ── Mock data ────────────────────────────────────────────────────────────────

MOCK_AI_RECOGNITION = {
    "food_items": [
        {
            "name": "dal tadka",
            "confidence": 0.91,
            "estimated_portion": "1 bowl",
            "estimated_weight_g": 200,
        },
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
    """Create a minimal 10x10 JPEG for upload tests."""
    from io import BytesIO

    from PIL import Image

    img = Image.new("RGB", (10, 10), color=(100, 150, 200))
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# ── Mock Redis + ARQ pool ────────────────────────────────────────────────────


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


class MockArqPool:
    """Mock ARQ pool that records enqueued jobs."""

    def __init__(self) -> None:
        self.jobs: list[tuple] = []

    async def enqueue_job(self, func_name: str, *args, **kwargs) -> None:
        self.jobs.append((func_name, args, kwargs))

    async def close(self) -> None:
        pass


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_redis() -> MockRedis:
    return MockRedis()


@pytest.fixture
def mock_arq_pool() -> MockArqPool:
    return MockArqPool()


def _override_redis_arq(mock_redis: MockRedis, mock_arq_pool: MockArqPool) -> None:
    """Set dependency overrides for Redis and ARQ pool."""
    from app.api.deps import get_arq_pool
    from app.core.redis import get_redis
    from app.main import app

    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_arq_pool] = lambda: mock_arq_pool


def _clear_redis_arq_overrides() -> None:
    """Remove dependency overrides for Redis and ARQ pool."""
    from app.api.deps import get_arq_pool
    from app.core.redis import get_redis
    from app.main import app

    app.dependency_overrides.pop(get_redis, None)
    app.dependency_overrides.pop(get_arq_pool, None)


def _get_user_id_from_headers(auth_headers: dict) -> str:
    """Extract user_id from auth headers by decoding the JWT."""
    from app.core.security import ACCESS_TOKEN_TYPE, verify_token

    token = auth_headers["Authorization"].removeprefix("Bearer ")
    return verify_token(token, expected_type=ACCESS_TOKEN_TYPE)


# ── Scan endpoint tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_meal_returns_pending(
    client: AsyncClient,
    profile_headers: dict,
    mock_redis: MockRedis,
    mock_arq_pool: MockArqPool,
):
    """POST /meals/scan returns 201 with scan_id and pending status."""
    _override_redis_arq(mock_redis, mock_arq_pool)
    try:
        with patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_upload:
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
        assert "scan_id" in data
        assert data["status"] == "pending"
        assert data["scan_id"] in data["poll_url"]

        # Verify ARQ job was enqueued
        assert len(mock_arq_pool.jobs) == 1
        assert mock_arq_pool.jobs[0][0] == "process_meal_scan"

        # Verify scan state was stored in Redis
        scan_key = f"{SCAN_KEY_PREFIX}{data['scan_id']}"
        assert scan_key in mock_redis.store
    finally:
        _clear_redis_arq_overrides()


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
    _override_redis_arq(MockRedis(), MockArqPool())
    try:
        resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("doc.pdf", b"fake pdf content", "application/pdf")},
            data={"meal_type": "lunch"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "MEAL_IMAGE_INVALID"
    finally:
        _clear_redis_arq_overrides()


@pytest.mark.asyncio
async def test_scan_requires_redis(client: AsyncClient, auth_headers: dict):
    """POST /meals/scan returns 503 when Redis is unavailable."""
    from app.api.deps import get_arq_pool
    from app.core.redis import get_redis
    from app.main import app

    app.dependency_overrides[get_redis] = lambda: None
    app.dependency_overrides[get_arq_pool] = lambda: None
    try:
        image_bytes = _make_test_image()
        resp = await client.post(
            "/api/v1/meals/scan",
            files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
            data={"meal_type": "lunch"},
            headers=auth_headers,
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "REDIS_UNAVAILABLE"
    finally:
        _clear_redis_arq_overrides()


@pytest.mark.asyncio
async def test_premium_gate_blocks_4th_scan(
    client: AsyncClient,
    auth_headers: dict,
    mock_redis: MockRedis,
    mock_arq_pool: MockArqPool,
):
    """Free users are blocked after 3 scans per day."""
    _override_redis_arq(mock_redis, mock_arq_pool)
    try:
        with patch("app.api.v1.meals.upload_image", new_callable=AsyncMock) as mock_up:
            mock_up.return_value = None
            image_bytes = _make_test_image()

            # Mock count_today_scans to simulate having 3 prior scans
            with patch(
                "app.api.v1.meals.meal_service.count_today_scans",
                new_callable=AsyncMock,
            ) as mock_count:
                mock_count.return_value = 3

                resp = await client.post(
                    "/api/v1/meals/scan",
                    files={"image": ("meal.jpg", image_bytes, "image/jpeg")},
                    data={"meal_type": "snack"},
                    headers=auth_headers,
                )
                assert resp.status_code == 403
                assert resp.json()["error"]["code"] == "PREMIUM_REQUIRED"
    finally:
        _clear_redis_arq_overrides()


# ── Scan status polling tests ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_status_pending(client: AsyncClient, auth_headers: dict):
    """Polling a pending scan returns correct state."""
    from app.core.redis import get_redis
    from app.main import app

    mock_redis = MockRedis()
    scan_id = str(uuid.uuid4())
    user_id = _get_user_id_from_headers(auth_headers)

    state = {
        "status": "pending",
        "user_id": user_id,
        "meal_type": "lunch",
        "image_url": None,
        "meal_id": None,
        "result": None,
        "error": None,
        "updated_at": "2026-03-06T00:00:00",
    }
    mock_redis.store[f"{SCAN_KEY_PREFIX}{scan_id}"] = json.dumps(state)
    app.dependency_overrides[get_redis] = lambda: mock_redis

    try:
        resp = await client.get(
            f"/api/v1/meals/scan/{scan_id}/status",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["scan_id"] == scan_id
        assert data["status"] == "pending"
        assert data["meal_id"] is None
        assert data["result"] is None
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_scan_status_completed(client: AsyncClient, auth_headers: dict):
    """Polling a completed scan returns meal_id and result."""
    from app.core.redis import get_redis
    from app.main import app
    from app.schemas.meal import MealScanResponse

    mock_redis = MockRedis()
    scan_id = str(uuid.uuid4())
    meal_id = str(uuid.uuid4())
    user_id = _get_user_id_from_headers(auth_headers)

    result_obj = MealScanResponse(
        meal_id=meal_id,
        meal_type="lunch",
        image_url=None,
        food_items=[],
        total_calories=182,
        total_protein_g=11,
        total_carbs_g=23,
        total_fat_g=5.6,
        total_fiber_g=4.4,
        ai_provider="gemini",
        ai_model="gemini-2.0-flash",
        analyzed_at="2026-03-06T12:00:00Z",
        recommendations=["Great job!"],
    )

    state = {
        "status": "completed",
        "user_id": user_id,
        "meal_type": "lunch",
        "image_url": None,
        "meal_id": meal_id,
        "result": result_obj.model_dump_json(),
        "error": None,
        "updated_at": "2026-03-06T00:00:00",
    }
    mock_redis.store[f"{SCAN_KEY_PREFIX}{scan_id}"] = json.dumps(state)
    app.dependency_overrides[get_redis] = lambda: mock_redis

    try:
        resp = await client.get(
            f"/api/v1/meals/scan/{scan_id}/status",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "completed"
        assert data["meal_id"] == meal_id
        assert data["result"]["total_calories"] == 182
        assert data["result"]["meal_id"] == meal_id
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_scan_status_failed(client: AsyncClient, auth_headers: dict):
    """Polling a failed scan returns error details."""
    from app.core.redis import get_redis
    from app.main import app

    mock_redis = MockRedis()
    scan_id = str(uuid.uuid4())
    user_id = _get_user_id_from_headers(auth_headers)

    state = {
        "status": "failed",
        "user_id": user_id,
        "meal_type": "lunch",
        "image_url": None,
        "meal_id": None,
        "result": None,
        "error": json.dumps({
            "code": "AI_ALL_PROVIDERS_FAILED",
            "message": "All AI providers failed",
        }),
        "updated_at": "2026-03-06T00:00:00",
    }
    mock_redis.store[f"{SCAN_KEY_PREFIX}{scan_id}"] = json.dumps(state)
    app.dependency_overrides[get_redis] = lambda: mock_redis

    try:
        resp = await client.get(
            f"/api/v1/meals/scan/{scan_id}/status",
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "failed"
        assert data["error"]["code"] == "AI_ALL_PROVIDERS_FAILED"
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_scan_status_not_found(client: AsyncClient, auth_headers: dict):
    """Polling an unknown scan_id returns 404."""
    from app.core.redis import get_redis
    from app.main import app

    mock_redis = MockRedis()
    app.dependency_overrides[get_redis] = lambda: mock_redis

    try:
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/meals/scan/{fake_id}/status",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "SCAN_NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_redis, None)


@pytest.mark.asyncio
async def test_scan_status_wrong_user(client: AsyncClient, auth_headers: dict):
    """Polling another user's scan returns 404 (not 403)."""
    from app.core.redis import get_redis
    from app.main import app

    mock_redis = MockRedis()
    scan_id = str(uuid.uuid4())

    state = {
        "status": "completed",
        "user_id": str(uuid.uuid4()),  # different user
        "meal_type": "lunch",
        "image_url": None,
        "meal_id": str(uuid.uuid4()),
        "result": None,
        "error": None,
        "updated_at": "2026-03-06T00:00:00",
    }
    mock_redis.store[f"{SCAN_KEY_PREFIX}{scan_id}"] = json.dumps(state)
    app.dependency_overrides[get_redis] = lambda: mock_redis

    try:
        resp = await client.get(
            f"/api/v1/meals/scan/{scan_id}/status",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "SCAN_NOT_FOUND"
    finally:
        app.dependency_overrides.pop(get_redis, None)


# ── Worker unit tests ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_meal_scan_worker_success(test_db):
    """Worker processes scan end-to-end and stores completed state."""
    import base64

    from app.models.user import User
    from app.services.scan_worker import process_meal_scan

    mock_redis = MockRedis()
    scan_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Create user in DB
    user = User(
        id=uuid.UUID(user_id), email="worker@test.com", name="Worker", hashed_password="x"
    )
    test_db.add(user)
    await test_db.commit()

    # Seed initial pending state
    await mock_redis.set(
        f"{SCAN_KEY_PREFIX}{scan_id}",
        json.dumps({"status": "pending", "user_id": user_id}),
    )

    image_bytes = _make_test_image()
    image_b64 = base64.b64encode(image_bytes).decode()

    def mock_session_factory() -> object:
        return test_db

    ctx = {"redis": mock_redis, "session_factory": mock_session_factory}

    with (
        patch(
            "app.services.ai_food_recognizer.AIFoodRecognizer"
        ) as mock_recognizer_cls,
        patch("app.services.nutrition_lookup.NutritionLookup") as mock_nutrition_cls,
        patch.object(test_db, "close", new_callable=AsyncMock),
    ):
        mock_rec = mock_recognizer_cls.return_value
        mock_rec.analyze_food_image = AsyncMock(return_value=MOCK_AI_RECOGNITION)
        mock_rec.estimate_nutrition = AsyncMock(return_value=MOCK_AI_NUTRITION)

        mock_nut = mock_nutrition_cls.return_value
        mock_nut.get_nutrition_with_cache = AsyncMock(return_value=MOCK_NUTRITION_SCALED)

        await process_meal_scan(
            ctx, scan_id, image_b64, "image/jpeg", user_id, "lunch", None, None
        )

    # Verify scan state is completed
    final_state = json.loads(mock_redis.store[f"{SCAN_KEY_PREFIX}{scan_id}"])
    assert final_state["status"] == "completed"
    assert final_state["meal_id"] is not None
    assert final_state["result"] is not None

    # Parse result and check it
    from app.schemas.meal import MealScanResponse

    result = MealScanResponse.model_validate_json(final_state["result"])
    assert result.total_calories > 0
    assert len(result.food_items) == 1
    assert result.food_items[0].name == "dal tadka"


@pytest.mark.asyncio
async def test_process_meal_scan_worker_ai_failure(test_db):
    """Worker catches AI error and stores failed state."""
    import base64

    from app.core.exceptions import AIProviderError
    from app.models.user import User
    from app.services.scan_worker import process_meal_scan

    mock_redis = MockRedis()
    scan_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    user = User(
        id=uuid.UUID(user_id), email="fail@test.com", name="Fail", hashed_password="x"
    )
    test_db.add(user)
    await test_db.commit()

    await mock_redis.set(
        f"{SCAN_KEY_PREFIX}{scan_id}",
        json.dumps({"status": "pending", "user_id": user_id}),
    )

    image_bytes = _make_test_image()
    image_b64 = base64.b64encode(image_bytes).decode()

    def mock_session_factory() -> object:
        return test_db

    ctx = {"redis": mock_redis, "session_factory": mock_session_factory}

    with (
        patch(
            "app.services.ai_food_recognizer.AIFoodRecognizer"
        ) as mock_recognizer_cls,
        patch.object(test_db, "close", new_callable=AsyncMock),
    ):
        mock_rec = mock_recognizer_cls.return_value
        mock_rec.analyze_food_image = AsyncMock(
            side_effect=AIProviderError("All AI providers failed")
        )

        await process_meal_scan(
            ctx, scan_id, image_b64, "image/jpeg", user_id, "lunch", None, None
        )

    # Verify scan state is failed
    final_state = json.loads(mock_redis.store[f"{SCAN_KEY_PREFIX}{scan_id}"])
    assert final_state["status"] == "failed"
    assert final_state["meal_id"] is None
    error = json.loads(final_state["error"])
    assert error["code"] == "SCAN_PROCESSING_FAILED"


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
