"""
Custom exception hierarchy for Swaq API.
All exceptions extend SwaqError and map to specific HTTP status codes.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class SwaqError(Exception):
    """Base exception. All custom errors extend this."""

    def __init__(
        self, message: str, code: str, status_code: int = 500, details: dict | None = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ValidationError(SwaqError):
    """400 — Request validation failed."""

    def __init__(self, message: str, code: str = "VALIDATION_ERROR", details: dict | None = None):
        super().__init__(message, code, 400, details)


class AuthenticationError(SwaqError):
    """401 — Authentication required or failed."""

    def __init__(self, message: str, code: str = "AUTH_TOKEN_INVALID"):
        super().__init__(message, code, 401)


class ForbiddenError(SwaqError):
    """403 — Authenticated but not authorized."""

    def __init__(self, message: str, code: str = "FORBIDDEN"):
        super().__init__(message, code, 403)


class NotFoundError(SwaqError):
    """404 — Resource not found."""

    def __init__(self, message: str, code: str = "NOT_FOUND"):
        super().__init__(message, code, 404)


class RateLimitError(SwaqError):
    """429 — Too many requests."""

    def __init__(
        self,
        message: str = "Too many requests. Please slow down.",
        code: str = "RATE_LIMIT_EXCEEDED",
    ):
        super().__init__(message, code, 429)


class AIProviderError(SwaqError):
    """502 — AI provider returned an error response."""

    def __init__(self, message: str, code: str = "AI_INVALID_RESPONSE"):
        super().__init__(message, code, 502)


class ServiceUnavailableError(SwaqError):
    """503 — All providers exhausted or service unavailable."""

    def __init__(
        self, message: str = "Service temporarily unavailable.", code: str = "SERVICE_UNAVAILABLE"
    ):
        super().__init__(message, code, 503)


# ── Pre-built instances for common cases ──────────────────────────────────────


def auth_invalid_credentials() -> AuthenticationError:
    return AuthenticationError("Invalid email or password.", "AUTH_INVALID_CREDENTIALS")


def auth_token_expired() -> AuthenticationError:
    return AuthenticationError("Access token has expired. Please refresh.", "AUTH_TOKEN_EXPIRED")


def auth_token_invalid() -> AuthenticationError:
    return AuthenticationError("Invalid or malformed token.", "AUTH_TOKEN_INVALID")


def auth_email_exists() -> ValidationError:
    return ValidationError("An account with this email already exists.", "AUTH_EMAIL_EXISTS")


def profile_not_found() -> NotFoundError:
    return NotFoundError(
        "Profile not found. Please create your profile first.", "PROFILE_NOT_FOUND"
    )


def meal_not_found() -> NotFoundError:
    return NotFoundError("Meal not found or does not belong to you.", "MEAL_NOT_FOUND")


def meal_scan_failed() -> ValidationError:
    return ValidationError(
        "Could not identify any food items in the image. Please try a clearer photo.",
        "MEAL_SCAN_FAILED",
    )


def meal_image_invalid() -> ValidationError:
    return ValidationError(
        "Unsupported image format. Please use JPEG, PNG, or WebP.",
        "MEAL_IMAGE_INVALID",
    )


def meal_image_too_large() -> ValidationError:
    return ValidationError("Image exceeds the 10MB size limit.", "MEAL_IMAGE_TOO_LARGE")


def ai_all_providers_failed() -> ServiceUnavailableError:
    return ServiceUnavailableError(
        "All AI providers are temporarily unavailable. Please try again in a moment.",
        "AI_ALL_PROVIDERS_FAILED",
    )


def scan_not_found() -> NotFoundError:
    return NotFoundError(
        "Scan not found or has expired.",
        "SCAN_NOT_FOUND",
    )


def premium_required() -> ForbiddenError:
    return ForbiddenError(
        "Free plan allows 3 scans/day. Upgrade to Premium for unlimited scans.",
        "PREMIUM_REQUIRED",
    )


# ── FastAPI exception handlers ─────────────────────────────────────────────────


async def swaq_error_handler(request: Request, exc: SwaqError) -> JSONResponse:
    """Global handler for all SwaqError subclasses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details if exc.details else None,
            },
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected server errors."""
    import logging

    logging.getLogger(__name__).exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "details": None,
            },
        },
    )
