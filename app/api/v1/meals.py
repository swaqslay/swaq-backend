"""
Meal endpoints — THIN controllers, all logic in meal_service / scan_processor.
POST   /api/v1/meals/scan             - Upload photo → inline AI scan → return full result
GET    /api/v1/meals/scan/{scan_id}/status - Deprecated: scans now complete inline
GET    /api/v1/meals/history          - Meal history for a date
GET    /api/v1/meals/{meal_id}        - Single meal detail
PATCH  /api/v1/meals/{meal_id}/items/{item_id} - Manual correction
DELETE /api/v1/meals/{meal_id}        - Delete meal
"""

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import meal_image_invalid, meal_image_too_large, premium_required
from app.core.redis import get_redis
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.meal import (
    MealDetailResponse,
    MealHistoryResponse,
    MealItemUpdate,
    MealScanResponse,
    QuickSnackInfo,
    QuickSnackListResponse,
    QuickSnackLogRequest,
    TextMealLogRequest,
)
from app.services import meal_service
from app.services.image_storage import upload_image
from app.services.scan_processor import process_scan_inline
from app.utils.constants import ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE_BYTES, QUICK_SNACKS
from app.utils.helpers import get_today_utc, parse_date

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/meals", tags=["Meals"])


@router.post("/scan", response_model=APIResponse[MealScanResponse], status_code=201)
async def scan_meal(
    image: UploadFile = File(..., description="Food photo (JPEG/PNG/WebP, max 10MB)"),
    meal_type: str = Form(default="snack", description="breakfast, lunch, dinner, snack"),
    notes: str = Form(default=""),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> APIResponse[MealScanResponse]:
    """
    Upload a food photo for AI analysis. Returns full nutrition breakdown inline.

    Flow:
    1. Validate image
    2. Check premium scan limit (3/day for free users)
    3. Upload to storage (optional — gracefully skipped if not configured)
    4. AI recognition + nutrition estimation (inline)
    5. Return full MealScanResponse
    """
    # ── 1. Validate image ─────────────────────────────────────────────────────
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise meal_image_invalid()

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise meal_image_too_large()

    # ── 2. Premium gate ───────────────────────────────────────────────────────
    if not current_user.is_premium:
        today_count = await meal_service.count_today_scans(current_user.id, db)
        if today_count >= settings.free_daily_scan_limit:
            raise premium_required()

    # ── 3. Upload to storage ──────────────────────────────────────────────────
    image_url = await upload_image(str(current_user.id), image_bytes, image.content_type)

    # ── 4. Inline processing ──────────────────────────────────────────────────
    result = await process_scan_inline(
        image_bytes=image_bytes,
        content_type=image.content_type,
        user_id=current_user.id,
        meal_type=meal_type,
        notes=notes or None,
        image_url=image_url,
        db=db,
        redis=redis,
    )
    return APIResponse.ok(result)


@router.get("/scan/{scan_id}/status", response_model=APIResponse[dict], deprecated=True)
async def get_scan_status(
    scan_id: str,
    current_user: User = Depends(get_current_active_user),
) -> APIResponse[dict]:
    """Deprecated: scans now complete inline. This endpoint is no longer needed."""
    return APIResponse.ok(
        {
            "message": "Scans now complete inline with POST /meals/scan. "
            "This polling endpoint is deprecated.",
            "scan_id": scan_id,
        }
    )


@router.get("/quick-snacks", response_model=APIResponse[QuickSnackListResponse])
async def list_quick_snacks() -> APIResponse[QuickSnackListResponse]:
    """Return the catalog of available quick snack shortcuts."""
    snacks = [
        QuickSnackInfo(
            id=snack_id,
            name=data["name"],
            emoji=data["emoji"],
            default_portion=data["default_portion"],
            calories=data["calories"],
            category=data["category"],
        )
        for snack_id, data in QUICK_SNACKS.items()
    ]
    return APIResponse.ok(QuickSnackListResponse(snacks=snacks))


@router.post("/log", response_model=APIResponse[MealScanResponse], status_code=201)
async def log_meal_text(
    data: TextMealLogRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> APIResponse[MealScanResponse]:
    """
    Log a meal via text input (no photo). Each food item goes through
    the nutrition lookup pipeline for macro/micro estimation.
    """
    # Premium gate — text logging counts toward daily scan limit
    if not current_user.is_premium:
        today_count = await meal_service.count_today_scans(current_user.id, db)
        if today_count >= settings.free_daily_scan_limit:
            raise premium_required()

    items = [item.model_dump() for item in data.items]
    meal = await meal_service.create_meal_from_text(
        user_id=current_user.id,
        meal_type=data.meal_type,
        items=items,
        notes=data.notes,
        db=db,
        redis=redis,
    )
    response = meal_service.build_meal_scan_response(meal)
    return APIResponse.ok(response)


@router.post("/quick-log", response_model=APIResponse[MealScanResponse], status_code=201)
async def log_quick_snack(
    data: QuickSnackLogRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[MealScanResponse]:
    """
    Log a quick snack shortcut. Uses pre-computed nutrition data —
    no external API calls, no premium gate.
    """
    meal = await meal_service.create_meal_from_quick_snack(
        user_id=current_user.id,
        snack_id=data.snack_id,
        quantity=data.quantity,
        meal_type=data.meal_type,
        db=db,
    )
    response = meal_service.build_meal_scan_response(meal)
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
