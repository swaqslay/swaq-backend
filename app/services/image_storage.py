"""
Backblaze B2 image storage service (S3-compatible API).
Handles upload, signed URL generation, and deletion.

Cloudflare R2 settings are retained in config for future migration.
"""

import asyncio
import logging

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.core.config import get_settings
from app.utils.helpers import generate_image_filename, mime_type_to_extension

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_b2_client():
    """Create and return an S3-compatible Backblaze B2 client."""
    return boto3.client(
        "s3",
        endpoint_url=settings.backblaze_b2_endpoint,
        aws_access_key_id=settings.backblaze_b2_access_key,
        aws_secret_access_key=settings.backblaze_b2_secret_key,
        region_name=settings.backblaze_b2_region or "us-west-004",
    )


def _is_configured() -> bool:
    """Return True if Backblaze B2 credentials are set."""
    return bool(settings.backblaze_b2_endpoint and settings.backblaze_b2_access_key)


async def upload_image(
    user_id: str,
    image_bytes: bytes,
    mime_type: str,
) -> str | None:
    """
    Upload an image to Backblaze B2 and return the object key.

    Args:
        user_id: Used as the folder prefix in B2.
        image_bytes: Raw image bytes.
        mime_type: MIME type of the image (e.g. "image/jpeg").

    Returns:
        The B2 object key (e.g. "user123/abc.jpg"), or None if upload fails.
    """
    if not _is_configured():
        logger.info("Backblaze B2 not configured — skipping image upload.")
        return None

    ext = mime_type_to_extension(mime_type)
    key = generate_image_filename(user_id, ext)

    try:
        client = _get_b2_client()
        await asyncio.to_thread(
            lambda: client.put_object(
                Bucket=settings.backblaze_b2_bucket,
                Key=key,
                Body=image_bytes,
                ContentType=mime_type,
            )
        )
        logger.info(f"Uploaded image to B2: {key}")
        return key
    except (ClientError, NoCredentialsError) as exc:
        logger.warning(f"B2 upload failed: {exc}. Continuing without image storage.")
        return None


def get_signed_url(key: str, expires_in: int = 3600) -> str | None:
    """
    Generate a pre-signed URL for accessing a B2 object.

    Args:
        key: The B2 object key.
        expires_in: URL expiry in seconds (default 1 hour).

    Returns:
        Pre-signed URL string, or None if B2 is not configured.
    """
    if not _is_configured() or not key:
        return None

    try:
        client = _get_b2_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.backblaze_b2_bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as exc:
        logger.warning(f"Failed to generate signed URL for {key}: {exc}")
        return None


async def delete_image(key: str) -> None:
    """
    Delete an image from B2. Silently fails if B2 is not configured.

    Args:
        key: The B2 object key to delete.
    """
    if not _is_configured() or not key:
        return

    try:
        client = _get_b2_client()
        await asyncio.to_thread(
            lambda: client.delete_object(Bucket=settings.backblaze_b2_bucket, Key=key)
        )
        logger.info(f"Deleted image from B2: {key}")
    except Exception as exc:
        logger.warning(f"B2 delete failed for {key}: {exc}")
