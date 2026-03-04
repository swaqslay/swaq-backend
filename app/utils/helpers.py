"""
Shared utility functions: normalization, date helpers, UUID, filename generation.
"""

import re
import uuid
from datetime import date, datetime, timezone


def normalize_food_name(name: str) -> str:
    """
    Normalize a food name for consistent cache key lookup.
    Lowercase, strip whitespace, remove special chars, collapse spaces.
    """
    normalized = name.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def get_today_utc() -> date:
    """Return today's date in UTC."""
    return datetime.now(timezone.utc).date()


def get_now_utc() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def parse_date(date_str: str) -> date:
    """
    Parse a date string in YYYY-MM-DD format.
    Raises ValueError if format is invalid.
    """
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")


def generate_image_filename(user_id: str, extension: str) -> str:
    """
    Generate a unique image filename for R2 storage.
    Format: {user_id}/{uuid4}.{ext}
    """
    unique_id = str(uuid.uuid4())
    ext = extension.lstrip(".")
    return f"{user_id}/{unique_id}.{ext}"


def mime_type_to_extension(mime_type: str) -> str:
    """Convert MIME type to file extension."""
    mapping = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }
    return mapping.get(mime_type, "jpg")
