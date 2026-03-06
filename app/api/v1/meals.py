"""
Meal endpoints — THIN controllers, all logic in meal_service / scan_worker.
POST   /api/v1/meals/scan             - Upload photo → enqueue async scan → return scan_id
GET    /api/v1/meals/scan/{scan_id}/status - Poll scan progress
GET    /api/v1/meals/history          - Meal history for a date
GET    /api/v1/meals/{meal_id}        - Single meal detail
PATCH  /api/v1/meals/{meal_id}/items/{item_id} - Manual correction
DELETE /api/v1/meals/{meal_id}        - Delete meal
"""

import base64
import json
import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_arq_pool, get_current_active_user
from app.core.database import get_db
from app.core.exceptions import (
    ServiceUnavailableError,
    meal_image_invalid,
    meal_image_too_large,
    premium_required,
    scan_not_found,
)
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.meal import (
    MealDetailResponse,
    MealHistoryResponse,
    MealItemUpdate,
    MealScanResponse,
    ScanStatusResponse,
    ScanSubmitResponse,
)
from app.services import meal_service
from app.services.image_storage import upload_image
from app.services.scan_worker import get_scan_state, set_scan_state
from app.utils.constants import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES
from app.utils.helpers import get_today_utc, parse_date

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/meals", tags=["Meals"])


@router.post("/scan", response_model=APIResponse[ScanSubmitResponse], status_code=201)
async def scan_meal(
    image: UploadFile = File(..., description="Food photo (JPEG/PNG/WebP, max 10MB)"),
    meal_type: str = Form(default="snack", description="breakfast, lunch, dinner, snack"),
    notes: str = Form(default=""),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    arq_pool=Depends(get_arq_pool),
) -> APIResponse[ScanSubmitResponse]:
    """
    Upload a food photo and enqueue async AI analysis.

    Returns a scan_id immediately. Poll GET /scan/{scan_id}/status for results.

    Flow:
    1. Validate image
    2. Check premium scan limit (3/day for free users)
    3. Upload to storage (optional — gracefully skipped if not configured)
    4. Enqueue ARQ job for background processing
    5. Return scan_id + poll_url
    """
    # ── 1. Require Redis + ARQ ────────────────────────────────────────────────
    if redis is None or arq_pool is None:
        raise ServiceUnavailableError(
            "Redis is required for meal scanning.", "REDIS_UNAVAILABLE"
        )

    # ── 2. Validate image ─────────────────────────────────────────────────────
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise meal_image_invalid()

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise meal_image_too_large()

    # ── 3. Premium gate ───────────────────────────────────────────────────────
    if not current_user.is_premium:
        from app.core.config import get_settings

        settings = get_settings()
        today_count = await meal_service.count_today_scans(current_user.id, db)
        if today_count >= settings.free_daily_scan_limit:
            raise premium_required()

    # ── 4. Upload to storage ──────────────────────────────────────────────────
    image_url = await upload_image(str(current_user.id), image_bytes, image.content_type)

    # ── 5. Generate scan_id and store initial state ───────────────────────────
    scan_id = str(uuid.uuid4())
    await set_scan_state(redis, scan_id, {
        "status": "pending",
        "user_id": str(current_user.id),
        "meal_type": meal_type,
        "image_url": image_url,
        "meal_id": None,
        "result": None,
        "error": None,
    })

    # ── 6. Enqueue ARQ job ────────────────────────────────────────────────────
    await arq_pool.enqueue_job(
        "process_meal_scan",
        scan_id,
        base64.b64encode(image_bytes).decode(),
        image.content_type,
        str(current_user.id),
        meal_type,
        notes or None,
        image_url,
    )

    poll_url = f"/api/v1/meals/scan/{scan_id}/status"
    return APIResponse.ok(
        ScanSubmitResponse(scan_id=scan_id, status="pending", poll_url=poll_url)
    )


@router.get("/scan/{scan_id}/status", response_model=APIResponse[ScanStatusResponse])
async def get_scan_status(
    scan_id: str,
    current_user: User = Depends(get_current_active_user),
    redis=Depends(get_redis),
) -> APIResponse[ScanStatusResponse]:
    """Poll the status of an async meal scan."""
    if redis is None:
        raise ServiceUnavailableError(
            "Redis is required for scan status.", "REDIS_UNAVAILABLE"
        )

    state = await get_scan_state(redis, scan_id)
    if state is None:
        raise scan_not_found()

    # Security: only the scan owner can poll
    if state.get("user_id") != str(current_user.id):
        raise scan_not_found()

    # Parse result/error from JSON strings if present
    result_data = None
    if state.get("result"):
        result_data = MealScanResponse.model_validate_json(state["result"])

    error_data = None
    if state.get("error"):
        error_data = json.loads(state["error"])

    response = ScanStatusResponse(
        scan_id=scan_id,
        status=state["status"],
        meal_id=state.get("meal_id"),
        result=result_data,
        error=error_data,
    )
    return APIResponse.ok(response)


@router.get("/history", response_model=APIResponse[MealHistoryResponse])
async def get_meal_history(
    date: str = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MealHistoryResponse]:
    """
    Get meal history for a specific date.

    Query params:
      - date: YYYY-MM-DD (defaults to today)
    """
    target_date = parse_date(date) if date else get_today_utc()
    history = await meal_service.get_meal_history(current_user.id, target_date, db)
    return APIResponse.ok(history)


@router.get("/{meal_id}", response_model=APIResponse[MealDetailResponse])
async def get_meal(
    meal_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MealDetailResponse]:
    """Get full details for a specific meal."""
    meal = await meal_service.get_meal(meal_id, current_user.id, db)
    return APIResponse.ok(meal_service.build_meal_detail_response(meal))


@router.patch("/{meal_id}/items/{item_id}", response_model=APIResponse[MealDetailResponse])
async def update_meal_item(
    meal_id: uuid.UUID,
    item_id: uuid.UUID,
    data: MealItemUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MealDetailResponse]:
    """
    Manually correct a food item in a meal.
    Also recalculates the meal's total nutrition.
    """
    meal = await meal_service.update_meal_item(meal_id, item_id, current_user.id, data, db)
    return APIResponse.ok(meal_service.build_meal_detail_response(meal))


@router.delete("/{meal_id}", response_model=APIResponse[dict], status_code=200)
async def delete_meal(
    meal_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Delete a meal and all its food items."""
    await meal_service.delete_meal(meal_id, current_user.id, db)
    return APIResponse.ok({"deleted": str(meal_id)})
