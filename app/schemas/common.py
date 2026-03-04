"""
Standard API response envelope used by all endpoints.
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error payload."""

    code: str
    message: str
    details: Optional[dict] = None


class APIResponse(BaseModel, Generic[T]):
    """
    Standard response envelope for all Swaq API endpoints.

    Success:  {"success": true,  "data": {...}, "error": null}
    Failure:  {"success": false, "data": null,  "error": {"code": ..., "message": ...}}
    """

    success: bool = True
    data: Optional[T] = None
    error: Optional[ErrorDetail] = None

    @classmethod
    def ok(cls, data: T) -> "APIResponse[T]":
        """Create a successful response."""
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, code: str, message: str, details: dict | None = None) -> "APIResponse":
        """Create an error response."""
        return cls(success=False, data=None, error=ErrorDetail(code=code, message=message, details=details))
